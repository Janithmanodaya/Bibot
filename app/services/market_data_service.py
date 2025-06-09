import logging
from app.services.binance_service import BinanceService
from app.services.db_service import get_user_setting, store_ohlc_data
from app.utils.encryption import ENCRYPTION_KEY # For decrypting stored API keys

logger = logging.getLogger(__name__)

def fetch_and_store_candles_from_binance(user_id, symbol, interval, start_str=None, end_str=None, limit=1000):
    logger.info(f"Attempting to fetch and store candles for {symbol} interval {interval} for user {user_id}")

    user_settings = get_user_setting(user_id=user_id)
    if not user_settings:
        logger.error(f"No user settings found for user_id {user_id}. Cannot fetch candles.")
        return False

    api_key = user_settings.get_api_key(ENCRYPTION_KEY)
    api_secret = user_settings.get_api_secret(ENCRYPTION_KEY)

    if not api_key or not api_secret:
        logger.error(f"API key or secret not configured for user_id {user_id}. Cannot fetch candles.")
        return False

    # Assuming testnet is False by default or configured elsewhere if needed
    binance_client = BinanceService(api_key=api_key, api_secret=api_secret)

    logger.info(f"Fetching historical candles for {symbol} interval {interval} from Binance...")
    try:
        candles_data = binance_client.get_historical_candles(symbol, interval, start_str=start_str, end_str=end_str, limit=limit)
        if candles_data:
            logger.info(f"Fetched {len(candles_data)} candles from Binance. Storing to DB...")
            # Ensure 'binance' is passed as exchange_name, matching what OHLCData expects if it's a string.
            store_ohlc_data(exchange='binance', symbol=symbol, timeframe=interval, candles_data=candles_data)
            logger.info(f"Successfully stored candles for {symbol} interval {interval}.")
            return True
        else:
            logger.info(f"No candle data received from Binance for {symbol} interval {interval}.")
            return False
    except Exception as e:
        logger.error(f"Error during fetching or storing candles for {symbol} interval {interval}: {e}")
        return False
