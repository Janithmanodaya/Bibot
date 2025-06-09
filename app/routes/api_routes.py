from flask import Blueprint, jsonify, request, current_app
from app.services import db_service, binance_service, market_data_service, strategy_service
from app.utils.encryption import ENCRYPTION_KEY
from app.models import UserSettings
import logging
import pandas as pd

bp = Blueprint('api', __name__)
logger = logging.getLogger(__name__)

def get_binance_service_instance(user_id=1):
    user_setting = db_service.get_user_setting(user_id=user_id)
    if not user_setting:
        logger.warning(f"No user settings found for user_id {user_id}")
        return None

    api_key = user_setting.get_api_key(ENCRYPTION_KEY)
    api_secret = user_setting.get_api_secret(ENCRYPTION_KEY)
    use_testnet = getattr(user_setting, 'use_testnet', False)

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
    user_id = 1
    if request.method == 'POST':
        data = request.json
        logger.info(f"API /settings POST called with data: {data}")
        try:
            use_testnet_val = data.get('use_testnet', False)
            if isinstance(use_testnet_val, str):
                 use_testnet_val = use_testnet_val.lower() in ['true', 'on', 'yes', '1']

            # Safely get float values, defaulting to None if not provided or empty string
            def get_float_or_none(val_name):
                val = data.get(val_name)
                if val == "" or val is None: return None
                try: return float(val)
                except ValueError: return None # Or raise error: return jsonify({'message': f'Invalid format for {val_name}'}), 400


            db_service.save_user_setting(
                user_id=user_id,
                api_key=data.get('api_key'),
                api_secret=data.get('api_secret'),
                exchange=data.get('exchange'),
                use_testnet=use_testnet_val,
                max_account_drawdown_percentage=get_float_or_none('max_account_drawdown_percentage'),
                max_trade_size_percentage_balance=get_float_or_none('max_trade_size_percentage_balance'),
                default_stop_loss_percentage=get_float_or_none('default_stop_loss_percentage'),
                peak_account_equity=get_float_or_none('peak_account_equity')
            )
            return jsonify({'message': 'Settings saved successfully!'}), 200
        except Exception as e:
            logger.error(f"Error saving settings: {e}", exc_info=True)
            return jsonify({'message': f'Error saving settings: {e}'}), 500
    else: # GET
        logger.info('API /settings GET called')
        user_setting = db_service.get_user_setting(user_id=user_id)
        if user_setting:
            return jsonify({
                'exchange': user_setting.selected_exchange,
                'api_key': user_setting.get_api_key(ENCRYPTION_KEY) or "",
                'api_secret': "", # Never send API secret back
                'use_testnet': getattr(user_setting, 'use_testnet', False),
                'max_account_drawdown_percentage': getattr(user_setting, 'max_account_drawdown_percentage', None),
                'max_trade_size_percentage_balance': getattr(user_setting, 'max_trade_size_percentage_balance', None),
                'default_stop_loss_percentage': getattr(user_setting, 'default_stop_loss_percentage', None),
                'peak_account_equity': getattr(user_setting, 'peak_account_equity', None)
            })
        # Return defaults if no settings found
        return jsonify({
            'exchange': 'binance', 'api_key': '', 'api_secret': '', 'use_testnet': False,
            'max_account_drawdown_percentage': 20.0,
            'max_trade_size_percentage_balance': 5.0,
            'default_stop_loss_percentage': 2.0,
            'peak_account_equity': 0.0
        })

@bp.route('/dashboard_data', methods=['GET'])
def get_dashboard_data():
    # ... (content from previous version, unchanged by this subtask) ...
    logger.info("API /dashboard_data GET called")
    user_id = 1
    bs = get_binance_service_instance(user_id)
    if not bs:
        return jsonify({
            'balance': {}, 'open_trades': [], 'trade_history': [],
            'error': 'API keys not configured or user settings not found.'
        }), 400
    try:
        balance = bs.get_account_balance() or {}
        open_trades = bs.get_open_orders() or []
        trade_history = bs.get_trade_history(symbol='BTCUSDT') or []
        return jsonify({ 'balance': balance, 'open_trades': open_trades, 'trade_history': trade_history })
    except Exception as e:
        logger.error(f"Error fetching dashboard data: {e}", exc_info=True)
        return jsonify({'error': f'Failed to fetch dashboard data: {e}'}), 500

@bp.route('/ohlc_data', methods=['GET'])
def get_ohlc_data_api():
    # ... (content from previous version, unchanged by this subtask) ...
    user_id = 1
    symbol = request.args.get('symbol', default='BTCUSDT', type=str)
    interval = request.args.get('timeframe', default='1h', type=str)
    limit = request.args.get('limit', default=100, type=int)
    logger.info(f"API /ohlc_data GET called for {symbol}, interval {interval}, limit {limit}")
    try:
        db_candles = db_service.get_ohlc_data(exchange_name='binance', symbol=symbol, timeframe=interval, limit=limit, sort_order='desc')
        if not db_candles or len(db_candles) < limit / 2:
            market_data_service.fetch_and_store_candles_from_binance(user_id=user_id, symbol=symbol, interval=interval, limit=limit)
            db_candles = db_service.get_ohlc_data(exchange_name='binance', symbol=symbol, timeframe=interval, limit=limit, sort_order='desc')
        if db_candles and len(db_candles) > 0 and db_candles[0].open_time > db_candles[-1].open_time: db_candles.reverse() # Check if db_candles is not empty
        chart_data = [{'x': c.open_time, 'o': c.open_price, 'h': c.high_price, 'l': c.low_price, 'c': c.close_price, 'v': c.volume} for c in db_candles]
        return jsonify(chart_data)
    except Exception as e:
        logger.error(f"Error fetching OHLC data for {symbol} {interval}: {e}", exc_info=True)
        return jsonify({'error': f'Failed to fetch OHLC data: {e}'}), 500

@bp.route('/strategies', methods=['GET'])
def get_strategies():
    # ... (content from previous version, unchanged by this subtask) ...
    logger.info("API /strategies GET called")
    predefined_strategies = [
        {"name": "MovingAverageCrossover", "params": strategy_service.MovingAverageCrossoverStrategy().params},
        {"name": "RSIOverboughtOversold", "params": strategy_service.RSIOverboughtOversoldStrategy().params},
        {"name": "MACDSignal", "params": strategy_service.MACDSignalStrategy().params}, # Added from prev step
        {"name": "BollingerBands", "params": strategy_service.BollingerBandsStrategy().params}, # Added from prev step
        {"name": "StochasticOscillator", "params": strategy_service.StochasticOscillatorStrategy().params}, # Added from prev step
    ]
    return jsonify(predefined_strategies)

@bp.route('/strategies/parameters', methods=['GET'])
def get_strategy_parameters():
    # ... (content from previous version, unchanged by this subtask) ...
    strategy_name = request.args.get('strategy_name')
    # Added from prev step
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


# --- Custom Strategy API Endpoints (from previous step) ---
@bp.route('/strategies/custom', methods=['POST'])
def create_new_custom_strategy():
    # ... (content from previous version, unchanged by this subtask) ...
    user_id = 1; data = request.json
    if not data or not data.get('name') or not data.get('configuration'): return jsonify({'error': 'Missing fields'}), 400
    try:
        strategy = db_service.create_custom_strategy(user_id, data['name'], data['configuration'], data.get('description'))
        return jsonify({'id': strategy.id, 'user_id': strategy.user_id, 'name': strategy.name, 'description': strategy.description, 'configuration': strategy.configuration}), 201
    except Exception as e: return jsonify({'error': str(e)}), 500

@bp.route('/strategies/custom', methods=['GET'])
def list_custom_strategies():
    # ... (content from previous version, unchanged by this subtask) ...
    user_id = 1
    try:
        strategies = db_service.get_all_custom_strategies(user_id)
        return jsonify([{'id':s.id, 'name':s.name, 'description':s.description, 'configuration':s.configuration} for s in strategies]), 200
    except Exception as e: return jsonify({'error': str(e)}), 500

@bp.route('/strategies/custom/<int:strategy_id>', methods=['GET'])
def get_specific_custom_strategy(strategy_id):
    # ... (content from previous version, unchanged by this subtask) ...
    user_id = 1
    try:
        strategy = db_service.get_custom_strategy(strategy_id, user_id)
        if not strategy: return jsonify({'error': 'Not found'}), 404
        return jsonify({'id':strategy.id, 'user_id': strategy.user_id, 'name':strategy.name, 'description':strategy.description, 'configuration':strategy.configuration}), 200
    except Exception as e: return jsonify({'error': str(e)}), 500

@bp.route('/strategies/custom/<int:strategy_id>', methods=['PUT'])
def update_specific_custom_strategy(strategy_id):
    # ... (content from previous version, unchanged by this subtask) ...
    user_id = 1; data = request.json;
    if not data: return jsonify({'error': 'No data'}), 400
    try:
        strategy = db_service.update_custom_strategy(strategy_id, user_id, data.get('name'), data.get('description'), data.get('configuration'))
        if not strategy: return jsonify({'error': 'Not found or no update'}), 404
        return jsonify({'id':strategy.id, 'user_id': strategy.user_id, 'name':strategy.name, 'description':strategy.description, 'configuration':strategy.configuration}), 200
    except Exception as e: return jsonify({'error': str(e)}), 500

@bp.route('/strategies/custom/<int:strategy_id>', methods=['DELETE'])
def delete_specific_custom_strategy(strategy_id):
    # ... (content from previous version, unchanged by this subtask) ...
    user_id = 1
    try:
        success = db_service.delete_custom_strategy(strategy_id, user_id)
        if not success: return jsonify({'error': 'Not found'}), 404
        return jsonify({'message': 'Deleted'}), 200
    except Exception as e: return jsonify({'error': str(e)}), 500

# Placeholders for start/stop strategy
@bp.route('/start_strategy', methods=['POST'])
def start_strategy(): return jsonify({'message': 'Strategy started (placeholder)'})
@bp.route('/stop_strategy', methods=['POST'])
def stop_strategy(): return jsonify({'message': 'Strategy stopped (placeholder)'})
