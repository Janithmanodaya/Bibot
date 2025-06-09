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
