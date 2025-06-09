from app import db
from app.models import UserSettings, TradeHistory, OHLCData, CustomStrategyModel
from app.utils.encryption import encrypt_data, decrypt_data, ENCRYPTION_KEY as APP_ENCRYPTION_KEY # Will be created in a later step
import logging

logger = logging.getLogger(__name__)
# ENCRYPTION_KEY = b'dummy_encryption_key_32bytes_123' # Placeholder, should be from config - REMOVED

def get_user_setting(user_id=1): # Assuming single user or user_id based retrieval
    return UserSettings.query.filter_by(user_id=user_id).first()

def save_user_setting(user_id=1, exchange='binance', api_key=None, api_secret=None, use_testnet=False):
    setting = get_user_setting(user_id)
    if not setting:
        setting = UserSettings(user_id=user_id)
    setting.selected_exchange = exchange
    setting.use_testnet = use_testnet # Added assignment for use_testnet
    if api_key and api_secret:
        # In a real app, ENCRYPTION_KEY would come from a secure config
        setting.set_api_credentials(api_key, api_secret, APP_ENCRYPTION_KEY)
    db.session.add(setting)
    try:
        db.session.commit()
        logger.info(f'UserSettings for user_id {user_id} saved.')
    except Exception as e:
        db.session.rollback()
        logger.error(f'Error saving UserSettings for user_id {user_id}: {e}')

def add_trade_history(order_id, exchange, symbol, type, side, price, quantity, status, exchange_timestamp=None):
    trade = TradeHistory(order_id=order_id, exchange=exchange, symbol=symbol, type=type, side=side, price=price, quantity=quantity, status=status, exchange_timestamp=exchange_timestamp)
    db.session.add(trade)
    try:
        db.session.commit()
        logger.info(f'TradeHistory for order_id {order_id} added.')
    except Exception as e:
        db.session.rollback()
        logger.error(f'Error adding TradeHistory for order_id {order_id}: {e}')

def store_ohlc_data(exchange, symbol, timeframe, candles_data):
    # candles_data is expected to be a list of lists/tuples from Binance client or similar
    # [open_time, open, high, low, close, volume, close_time, ...]
    for data in candles_data:
        ohlc_entry = OHLCData.query.filter_by(exchange=exchange, symbol=symbol, timeframe=timeframe, open_time=data[0]).first()
        if not ohlc_entry:
            ohlc_entry = OHLCData(
                exchange=exchange,
                symbol=symbol,
                timeframe=timeframe,
                open_time=data[0],
                open_price=float(data[1]),
                high_price=float(data[2]),
                low_price=float(data[3]),
                close_price=float(data[4]),
                volume=float(data[5]),
                close_time=data[6]
            )
            db.session.add(ohlc_entry)
        else: # Update if exists, though Binance data is usually static for closed candles
            ohlc_entry.open_price=float(data[1])
            ohlc_entry.high_price=float(data[2])
            ohlc_entry.low_price=float(data[3])
            ohlc_entry.close_price=float(data[4])
            ohlc_entry.volume=float(data[5])
            ohlc_entry.close_time=data[6]

    try:
        db.session.commit()
        logger.info(f'Stored/Updated {len(candles_data)} OHLC entries for {symbol} {timeframe}.')
    except Exception as e:
        db.session.rollback()
        logger.error(f'Error storing OHLC data for {symbol} {timeframe}: {e}')

def get_ohlc_data(exchange_name, symbol, timeframe, start_time_ms=None, end_time_ms=None, limit=None, sort_order='asc'):
    logger.info(f"Fetching OHLC data for {exchange_name} {symbol} {timeframe}")
    query = OHLCData.query.filter_by(exchange=exchange_name, symbol=symbol, timeframe=timeframe)

    if start_time_ms:
        query = query.filter(OHLCData.open_time >= start_time_ms)
    if end_time_ms:
        query = query.filter(OHLCData.open_time <= end_time_ms)

    if sort_order == 'desc':
        query = query.order_by(OHLCData.open_time.desc())
    else:
        query = query.order_by(OHLCData.open_time.asc())

    if limit:
        query = query.limit(limit)

    results = query.all()
    logger.info(f"Retrieved {len(results)} OHLC records for {exchange_name} {symbol} {timeframe}")
    return results

# --- Custom Strategy CRUD ---

def create_custom_strategy(user_id, name, configuration, description=None):
    logger.info(f"Creating custom strategy '{name}' for user_id {user_id}")
    try:
        strategy = CustomStrategyModel(
            user_id=user_id,
            name=name,
            description=description,
            configuration=configuration
        )
        db.session.add(strategy)
        db.session.commit()
        logger.info(f"Custom strategy '{name}' created with id {strategy.id}")
        return strategy
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating custom strategy '{name}': {e}", exc_info=True)
        raise # Re-raise the exception to be handled by the caller

def get_custom_strategy(strategy_id, user_id): # user_id for ownership check
    logger.info(f"Fetching custom strategy id {strategy_id} for user_id {user_id}")
    # In a multi-user app, ensure user_id matches.
    return CustomStrategyModel.query.filter_by(id=strategy_id, user_id=user_id).first()

def get_all_custom_strategies(user_id):
    logger.info(f"Fetching all custom strategies for user_id {user_id}")
    return CustomStrategyModel.query.filter_by(user_id=user_id).all()

def update_custom_strategy(strategy_id, user_id, name=None, description=None, configuration=None):
    logger.info(f"Updating custom strategy id {strategy_id} for user_id {user_id}")
    strategy = CustomStrategyModel.query.filter_by(id=strategy_id, user_id=user_id).first()
    if not strategy:
        logger.warning(f"Custom strategy id {strategy_id} not found for user_id {user_id}")
        return None # Or raise a custom NotFound error

    updated = False
    if name is not None and strategy.name != name:
        strategy.name = name
        updated = True
    if description is not None and strategy.description != description:
        strategy.description = description
        updated = True
    if configuration is not None and strategy.configuration != configuration: # Deep comparison might be needed for JSON
        strategy.configuration = configuration
        updated = True

    if updated:
        try:
            db.session.commit()
            logger.info(f"Custom strategy id {strategy_id} updated.")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating custom strategy id {strategy_id}: {e}", exc_info=True)
            raise
    return strategy

def delete_custom_strategy(strategy_id, user_id):
    logger.info(f"Deleting custom strategy id {strategy_id} for user_id {user_id}")
    strategy = CustomStrategyModel.query.filter_by(id=strategy_id, user_id=user_id).first()
    if not strategy:
        logger.warning(f"Custom strategy id {strategy_id} not found for deletion for user_id {user_id}")
        return False # Or raise NotFound

    try:
        db.session.delete(strategy)
        db.session.commit()
        logger.info(f"Custom strategy id {strategy_id} deleted.")
        return True
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting custom strategy id {strategy_id}: {e}", exc_info=True)
        raise
