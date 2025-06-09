from flask_socketio import emit
import logging

# Logger for this module's specific logs, not for forwarding general app logs.
logger = logging.getLogger(__name__)
# Prevent this logger's messages from being handled by the root logger's SocketIOHandler again
# if they were already processed by it, or if this logger is only for internal debug.
logger.propagate = False

sio_instance = None # Will be set by app factory in app/__init__.py

def send_log_to_frontend_via_sio(log_message_data):
    """
    Emits a log message to the frontend using the globally set SocketIO instance.
    This function is intended to be used by the SocketIOHandler.
    """
    if sio_instance:
        sio_instance.emit('log_message', {'data': log_message_data})
    # else:
        # This else block would be problematic as print goes to stdout
        # and might not be visible. Proper setup of sio_instance is key.
        # print(f"Debug: sio_instance not set. Log not sent: {log_message_data}")


def register_socketio_handlers(sio):
    """
    Registers SocketIO event handlers.
    Called from app factory after SocketIO is initialized.
    """
    global sio_instance
    sio_instance = sio

    @sio.on('connect')
    def handle_connect():
        logger.info('Client connected to WebSocket') # This log will go to console/file
        emit('status', {'data': 'Connected to server WebSocket'})

    @sio.on('disconnect')
    def handle_disconnect():
        logger.info('Client disconnected from WebSocket') # This log will go to console/file

    @sio.on('request_data')
    def handle_request_data(json_data): # Renamed from 'json' to avoid conflict
        logger.info(f'Received WebSocket request_data: {json_data}') # This log will go to console/file
        emit('data_update', {'data': 'Sample data update in response to request', 'request': json_data})

    from binance import ThreadedWebsocketManager
    from flask import current_app

    # --- Binance WebSocket for Price Updates ---
    twm = None
    active_streams = {} # symbol: stream_name

    def start_twm():
        global twm
        if not twm:
            logger.info("Initializing ThreadedWebsocketManager")
            # Ensure API key and secret are available; otherwise, TWM might not authenticate for private streams if needed
            # For public streams like miniTicker, API key/secret are not strictly necessary for starting TWM itself,
            # but good practice if other private calls might be made or if Binance changes requirements.
            binance_api_key = current_app.config.get('BINANCE_API_KEY')
            binance_api_secret = current_app.config.get('BINANCE_API_SECRET')
            if not binance_api_key or not binance_api_secret:
                logger.warning("Binance API Key/Secret not configured. WebSocket functionality may be limited.")
                # Decide if TWM should start without credentials or not.
                # For public market data streams, it might be fine.
                # For user data streams, it will fail.

            twm = ThreadedWebsocketManager(api_key=binance_api_key, api_secret=binance_api_secret)
            twm.start()
            logger.info("ThreadedWebsocketManager started")

    def price_update_callback(msg):
        # Callback for processing messages from Binance WebSocket
        # Determine msg_data (either msg or msg['data'])
        # Binance ThreadedWebsocketManager nests the actual data inside a 'data' key,
        # and the stream name is in 'stream'.
        if msg and isinstance(msg, dict) and msg.get('stream') and 'miniTicker' in msg['stream'] and isinstance(msg.get('data'), dict):
            msg_data = msg['data']
        # Handling for direct messages if not nested under 'data' (less common with TWM for specific streams)
        elif msg and isinstance(msg, dict) and msg.get('e') == '24hrMiniTicker' and 'data' not in msg : # Check event type for direct message
            msg_data = msg
        else:
            # logger.debug(f"Received message that is not a miniTicker or has unexpected structure: {msg}")
            return # Not the message type we are looking for

        symbol = msg_data.get('s')      # Symbol
        price = msg_data.get('c')       # Close price
        event_time = msg_data.get('E')  # Event time

        if not (symbol and price and event_time):
            # logger.debug(f"Missing symbol, price, or event_time in miniTicker data: {msg_data}")
            return

        if sio_instance:
            # logger.debug(f"Emitting price_update: symbol={symbol}, price={price}, event_time={event_time}")
            sio_instance.emit('price_update', {'symbol': symbol, 'price': price, 'event_time': event_time})

    @sio.on('subscribe_to_symbol_price')
    def handle_subscribe_to_symbol_price(data):
        global twm, active_streams
        symbol = data.get('symbol')
        if not symbol:
            logger.error("No symbol provided for price subscription")
            emit('status', {'data': 'Error: No symbol provided for price subscription'})
            return

        if not twm: # Ensure TWM is running
            start_twm()
            if not twm: # If start_twm failed (e.g. API keys missing and decided not to start)
                logger.error("ThreadedWebsocketManager could not be started.")
                emit('status', {'data': 'Error: WebSocket manager could not be started.'})
                return

        # Normalize symbol for stream name (e.g., BTCUSDT -> btcusdt)
        # stream_symbol = symbol.lower() # Not directly used for starting, but good for reference
        # stream_name = f"{stream_symbol}@miniTicker" # The actual stream name might vary slightly

        if symbol in active_streams:
            logger.info(f"Already subscribed to {symbol}")
            emit('status', {'data': f'Already subscribed to {symbol}'})
            return

        if twm:
            logger.info(f"Subscribing to price updates for {symbol}")
            # Note: The `symbol` parameter for `start_symbol_miniticker_socket` should be uppercase (e.g., BTCUSDT)
            # as per python-binance library usage for specific symbol streams.
            actual_stream_name = twm.start_symbol_miniticker_socket(symbol=symbol.upper(), callback=price_update_callback)
            # The actual_stream_name returned by start_symbol_miniticker_socket is what should be used for stopping.
            active_streams[symbol] = actual_stream_name
            emit('status', {'data': f'Subscribed to price updates for {symbol}'})
        else: # Should be caught by the twm check after start_twm()
            logger.error("ThreadedWebsocketManager not available for subscription.")
            emit('status', {'data': 'Error: WebSocket manager not available.'})


    @sio.on('unsubscribe_from_symbol_price')
    def handle_unsubscribe_from_symbol_price(data):
        global twm, active_streams
        symbol = data.get('symbol')
        if not symbol:
            logger.error("No symbol provided for price unsubscription")
            emit('status', {'data': 'Error: No symbol provided for price unsubscription'})
            return

        stream_name_to_stop = active_streams.pop(symbol, None)
        if stream_name_to_stop and twm:
            logger.info(f"Unsubscribing from price updates for {symbol} (stream: {stream_name_to_stop})")
            twm.stop_socket(stream_name_to_stop)
            emit('status', {'data': f'Unsubscribed from price updates for {symbol}'})
            # Consider stopping TWM if no streams are active:
            if not active_streams and twm: # Check active_streams after pop
                logger.info("No active streams, stopping ThreadedWebsocketManager")
                twm.stop() # This stops all sockets and the TWM thread.
                twm = None
        else:
            logger.warning(f"Not subscribed to {symbol} or TWM not available.")
            emit('status', {'data': f'Not currently subscribed to {symbol} or WebSocket manager not available.'})

    # It's good practice to ensure TWM is stopped when the app exits.
    # A proper Flask app would use app.teardown_appcontext or similar.
    # For now, the TWM thread might keep running until the main process is killed.
    # Consider adding a cleanup function for twm.stop() if sio.on_disconnect is too broad or
    # if you want to manage TWM lifecycle more explicitly (e.g. on server shutdown).

    # Other app-specific SocketIO events can be registered here too.

    # After handlers are registered and sio_instance is set,
    # inform the SocketIOHandler about the emitter function.
    # This requires getting the handler instance from the root logger.
    # This is a bit of a deferred setup.
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        if hasattr(handler, 'set_emitter') and callable(handler.set_emitter):
            # Found our custom handler (presumably SocketIOHandler)
            handler.set_emitter(send_log_to_frontend_via_sio)
            logger.info("SocketIO emitter configured for log handler.")
            break
    else:
        logger.warning("SocketIOHandler not found or set_emitter not available. Frontend logs from handler disabled.")
