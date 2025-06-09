from flask import Blueprint, jsonify, request, current_app
from app.services import db_service, binance_service, market_data_service, strategy_service
from app.utils.encryption import ENCRYPTION_KEY # This is the key derived in encryption.py
from app.models import UserSettings # To access get_api_key methods directly if needed for response shaping
import logging
import pandas as pd

bp = Blueprint('api', __name__)
logger = logging.getLogger(__name__)

# Helper to get BinanceService instance
def get_binance_service_instance(user_id=1):
    user_setting = db_service.get_user_setting(user_id=user_id)
    if not user_setting:
        logger.warning(f"No user settings found for user_id {user_id}")
        return None

    api_key = user_setting.get_api_key(ENCRYPTION_KEY)
    api_secret = user_setting.get_api_secret(ENCRYPTION_KEY)
    use_testnet = getattr(user_setting, 'use_testnet', False) # Assuming 'use_testnet' attr exists

    if not api_key or not api_secret:
        logger.warning(f"API key or secret not configured for user_id {user_id}")
        return None

    return binance_service.BinanceService(api_key=api_key, api_secret=api_secret, testnet=use_testnet)

@bp.route('/status', methods=['GET'])
def get_status():
    logger.info('API /status called')
    return jsonify({'status': 'API is running'})

@bp.route('/settings', methods=['GET', 'POST'])
def manage_settings():
    user_id = 1 # Assuming single user context for now
    if request.method == 'POST':
        data = request.json
        logger.info(f"API /settings POST called with data: {data}")
        try:
            # use_testnet is a boolean, ensure it's handled correctly
            use_testnet_val = data.get('use_testnet', False)
            if isinstance(use_testnet_val, str): # Handle 'on' or 'true' from checkbox if not parsed by JS
                 use_testnet_val = use_testnet_val.lower() in ['true', 'on', 'yes', '1']

            db_service.save_user_setting(
                user_id=user_id,
                api_key=data.get('api_key'),
                api_secret=data.get('api_secret'),
                exchange=data.get('exchange'),
                use_testnet=use_testnet_val # Pass to db_service
            )
            return jsonify({'message': 'Settings saved successfully!'}), 200
        except Exception as e:
            logger.error(f"Error saving settings: {e}", exc_info=True)
            return jsonify({'message': f'Error saving settings: {e}'}), 500
    else: # GET
        logger.info('API /settings GET called')
        user_setting = db_service.get_user_setting(user_id=user_id)
        if user_setting:
            api_key_decrypted = user_setting.get_api_key(ENCRYPTION_KEY)
            # For security, typically don't send full secret. Send placeholder or just if set.
            # However, the form implies editing, so for now, we might send it.
            # Consider sending a masked version or only on explicit request for actual use.
            api_secret_decrypted = user_setting.get_api_secret(ENCRYPTION_KEY)
            use_testnet_val = getattr(user_setting, 'use_testnet', False)

            return jsonify({
                'exchange': user_setting.selected_exchange,
                'api_key': api_key_decrypted if api_key_decrypted else "",
                'api_secret': api_secret_decrypted if api_secret_decrypted else "", # Be cautious with this
                'use_testnet': use_testnet_val
            })
        return jsonify({'exchange': 'binance', 'api_key': '', 'api_secret': '', 'use_testnet': False})


@bp.route('/dashboard_data', methods=['GET'])
def get_dashboard_data():
    logger.info("API /dashboard_data GET called")
    user_id = 1
    bs = get_binance_service_instance(user_id)
    if not bs:
        return jsonify({
            'balance': {},
            'open_trades': [],
            'trade_history': [],
            'error': 'API keys not configured or user settings not found.'
        }), 400

    try:
        balance = bs.get_account_balance() or {}
        open_trades = bs.get_open_orders() or [] # Assuming get_open_orders for "open trades"
        # For trade history, let's try to get for a common symbol or allow 'all' if supported
        # This might need a default symbol or user preference
        trade_history = bs.get_trade_history(symbol='BTCUSDT') or []
        # If no symbol is good, one might iterate over assets in balance and get history, or provide UI to select.
        # For now, BTCUSDT is a placeholder.

        return jsonify({
            'balance': balance,
            'open_trades': open_trades,
            'trade_history': trade_history
        })
    except Exception as e:
        logger.error(f"Error fetching dashboard data: {e}", exc_info=True)
        return jsonify({'error': f'Failed to fetch dashboard data: {e}'}), 500

@bp.route('/ohlc_data', methods=['GET'])
def get_ohlc_data_api():
    user_id = 1 # For API key access via market_data_service
    symbol = request.args.get('symbol', default='BTCUSDT', type=str)
    interval = request.args.get('timeframe', default='1h', type=str) # 'interval' for Binance, 'timeframe' in UI
    limit = request.args.get('limit', default=100, type=int)
    # start_str/end_str can also be added as params if needed by fetch_and_store_candles_from_binance

    logger.info(f"API /ohlc_data GET called for {symbol}, interval {interval}, limit {limit}")

    try:
        # Attempt to fetch from DB first
        db_candles = db_service.get_ohlc_data(
            exchange_name='binance',
            symbol=symbol,
            timeframe=interval,
            limit=limit,
            sort_order='desc' # Get most recent data
        )

        # If DB has fewer than requested limit, try to fetch more from Binance
        # (Simple logic: if db data is less than half of requested, fetch from exchange)
        # A more robust solution would check timestamps and fill gaps.
        if not db_candles or len(db_candles) < limit / 2:
            logger.info(f"Insufficient data in DB for {symbol}/{interval} ({len(db_candles)} found, wanted {limit}). Fetching from exchange.")
            market_data_service.fetch_and_store_candles_from_binance(
                user_id=user_id,
                symbol=symbol,
                interval=interval,
                limit=limit # Fetch up to limit
            )
            # Re-query DB after fetching
            db_candles = db_service.get_ohlc_data(
                exchange_name='binance',
                symbol=symbol,
                timeframe=interval,
                limit=limit,
                sort_order='desc'
            )

        if db_candles:
             # Reverse if fetched in desc order for chronological display in charts
            if db_candles[0].open_time > db_candles[-1].open_time:
                 db_candles.reverse()

        # Format for Chart.js (example: array of {x: timestamp_ms, o: open, h: high, l: low, c: close})
        chart_data = [{
            'x': candle.open_time, # Assuming open_time is a JS compatible timestamp (ms)
            'o': candle.open_price,
            'h': candle.high_price,
            'l': candle.low_price,
            'c': candle.close_price,
            'v': candle.volume # Optional: include volume
        } for candle in db_candles]

        return jsonify(chart_data)
    except Exception as e:
        logger.error(f"Error fetching OHLC data for {symbol} {interval}: {e}", exc_info=True)
        return jsonify({'error': f'Failed to fetch OHLC data: {e}'}), 500

@bp.route('/strategies', methods=['GET'])
def get_strategies():
    logger.info("API /strategies GET called")
    # strategy_service should ideally provide a way to list strategies and their default params
    predefined_strategies = [
        {"name": "MovingAverageCrossover", "params": strategy_service.MovingAverageCrossoverStrategy().params},
        {"name": "RSIOverboughtOversold", "params": strategy_service.RSIOverboughtOversoldStrategy().params},
        {"name": "MACDSignal", "params": strategy_service.MACDSignalStrategy().params},
        {"name": "BollingerBands", "params": strategy_service.BollingerBandsStrategy().params},
        {"name": "StochasticOscillator", "params": strategy_service.StochasticOscillatorStrategy().params},
    ]
    # Custom strategies could be loaded from db_service.get_custom_strategies() in future
    return jsonify(predefined_strategies)

@bp.route('/strategies/parameters', methods=['GET'])
def get_strategy_parameters():
    strategy_name = request.args.get('strategy_name')
    logger.info(f"API /strategies/parameters GET called for {strategy_name}")

    strategy_class_map = {
        "MovingAverageCrossover": strategy_service.MovingAverageCrossoverStrategy,
        "RSIOverboughtOversold": strategy_service.RSIOverboughtOversoldStrategy,
        "MACDSignal": strategy_service.MACDSignalStrategy,
        "BollingerBands": strategy_service.BollingerBandsStrategy,
        "StochasticOscillator": strategy_service.StochasticOscillatorStrategy,
    }

    strategy_cls = strategy_class_map.get(strategy_name)
    if strategy_cls:
        return jsonify(strategy_cls().params)
    else:
        return jsonify({'error': 'Strategy not found'}), 404

# Placeholder for existing strategy endpoints, can be developed further
@bp.route('/start_strategy', methods=['POST'])
def start_strategy():
    data = request.json
    logger.info(f'API /start_strategy called with data: {data}')
    # Actual implementation would involve:
    # 1. Validating strategy config (data)
    # 2. Storing active strategy state (e.g., in DB or memory store like Redis)
    # 3. Initializing and starting a background task/thread for the strategy execution loop
    return jsonify({'message': 'Strategy started (placeholder)', 'strategy': data.get('strategyName')})

@bp.route('/stop_strategy', methods=['POST'])
def stop_strategy():
    # Needs identifier for which strategy to stop
    strategy_id = request.json.get('strategy_id')
    logger.info(f'API /stop_strategy called for {strategy_id}')
    # Actual implementation:
    # 1. Find active strategy task/thread
    # 2. Signal it to stop gracefully
    # 3. Update its state in DB/memory store
    return jsonify({'message': 'Strategy stopped (placeholder)'})

# --- Custom Strategy API Endpoints ---

@bp.route('/strategies/custom', methods=['POST'])
def create_new_custom_strategy():
    user_id = 1 # Assuming single user context
    data = request.json
    if not data or not data.get('name') or not data.get('configuration'):
        return jsonify({'error': 'Missing required fields: name and configuration'}), 400

    try:
        strategy = db_service.create_custom_strategy(
            user_id=user_id,
            name=data['name'],
            description=data.get('description'),
            configuration=data['configuration']
        )
        # Return a representation of the created strategy
        # Manually construct dict to avoid issues with non-serializable SQLAlchemy objects directly
        strategy_data = {
            'id': strategy.id,
            'user_id': strategy.user_id,
            'name': strategy.name,
            'description': strategy.description,
            'configuration': strategy.configuration
        }
        return jsonify(strategy_data), 201
    except Exception as e:
        logger.error(f"Error creating custom strategy via API: {e}", exc_info=True)
        return jsonify({'error': f'Could not create custom strategy: {e}'}), 500

@bp.route('/strategies/custom', methods=['GET'])
def list_custom_strategies():
    user_id = 1 # Assuming single user context
    try:
        strategies = db_service.get_all_custom_strategies(user_id=user_id)
        strategies_data = [{
            'id': s.id, 'name': s.name, 'description': s.description,
            'configuration': s.configuration # Ensure this is serializable
        } for s in strategies]
        return jsonify(strategies_data), 200
    except Exception as e:
        logger.error(f"Error listing custom strategies via API: {e}", exc_info=True)
        return jsonify({'error': f'Could not list custom strategies: {e}'}), 500

@bp.route('/strategies/custom/<int:strategy_id>', methods=['GET'])
def get_specific_custom_strategy(strategy_id):
    user_id = 1 # Assuming single user context
    try:
        strategy = db_service.get_custom_strategy(strategy_id=strategy_id, user_id=user_id)
        if not strategy:
            return jsonify({'error': 'Custom strategy not found'}), 404

        strategy_data = {
            'id': strategy.id, 'user_id': strategy.user_id, 'name': strategy.name,
            'description': strategy.description, 'configuration': strategy.configuration
        }
        return jsonify(strategy_data), 200
    except Exception as e:
        logger.error(f"Error fetching custom strategy {strategy_id} via API: {e}", exc_info=True)
        return jsonify({'error': f'Could not fetch custom strategy: {e}'}), 500

@bp.route('/strategies/custom/<int:strategy_id>', methods=['PUT'])
def update_specific_custom_strategy(strategy_id):
    user_id = 1 # Assuming single user context
    data = request.json
    if not data:
        return jsonify({'error': 'No data provided for update'}), 400

    try:
        # Ensure at least one updatable field is present, or allow partial updates.
        # db_service.update_custom_strategy handles None for fields not being updated.
        strategy = db_service.update_custom_strategy(
            strategy_id=strategy_id,
            user_id=user_id,
            name=data.get('name'),
            description=data.get('description'),
            configuration=data.get('configuration')
        )
        if not strategy:
            return jsonify({'error': 'Custom strategy not found or no update performed'}), 404 # Or 304 if no change

        strategy_data = {
            'id': strategy.id, 'user_id': strategy.user_id, 'name': strategy.name,
            'description': strategy.description, 'configuration': strategy.configuration
        }
        return jsonify(strategy_data), 200
    except Exception as e:
        logger.error(f"Error updating custom strategy {strategy_id} via API: {e}", exc_info=True)
        return jsonify({'error': f'Could not update custom strategy: {e}'}), 500

@bp.route('/strategies/custom/<int:strategy_id>', methods=['DELETE'])
def delete_specific_custom_strategy(strategy_id):
    user_id = 1 # Assuming single user context
    try:
        success = db_service.delete_custom_strategy(strategy_id=strategy_id, user_id=user_id)
        if not success:
            return jsonify({'error': 'Custom strategy not found or could not be deleted'}), 404
        return jsonify({'message': f'Custom strategy {strategy_id} deleted successfully'}), 200
    except Exception as e:
        logger.error(f"Error deleting custom strategy {strategy_id} via API: {e}", exc_info=True)
        return jsonify({'error': f'Could not delete custom strategy: {e}'}), 500
