from app import db
from app.models import UserSetting, TradeHistory, OHLCData
from app.utils.encryption import encrypt_data, decrypt_data # Will be created in a later step
import logging

logger = logging.getLogger(__name__)
ENCRYPTION_KEY = b'dummy_encryption_key_32bytes_123' # Placeholder, should be from config

def get_user_setting(user_id=1): # Assuming single user or user_id based retrieval
    return UserSetting.query.filter_by(user_id=user_id).first()

def save_user_setting(user_id=1, exchange='binance', api_key=None, api_secret=None):
    setting = get_user_setting(user_id)
    if not setting:
        setting = UserSetting(user_id=user_id)
    setting.selected_exchange = exchange
    if api_key and api_secret:
        # In a real app, ENCRYPTION_KEY would come from a secure config
        setting.set_api_credentials(api_key, api_secret, ENCRYPTION_KEY)
    db.session.add(setting)
    try:
        db.session.commit()
        logger.info(f'UserSetting for user_id {user_id} saved.')
    except Exception as e:
        db.session.rollback()
        logger.error(f'Error saving UserSetting for user_id {user_id}: {e}')

def add_trade_history(order_id, exchange, symbol, type, side, price, quantity, status):
    trade = TradeHistory(order_id=order_id, exchange=exchange, symbol=symbol, type=type, side=side, price=price, quantity=quantity, status=status)
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
