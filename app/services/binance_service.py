from .exchange_service import ExchangeService
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceRequestException
import logging

logger = logging.getLogger(__name__)

class BinanceService(ExchangeService):
    def __init__(self, api_key, api_secret, testnet=False):
        super().__init__(api_key, api_secret)
        self.client = Client(api_key, api_secret, testnet=testnet)

    def get_account_balance(self):
        logger.info('Fetching account balance from Binance')
        # Placeholder implementation
        try:
            account_info = self.client.get_account()
            balances = {item['asset']: item['free'] for item in account_info.get('balances', []) if float(item['free']) > 0}
            logger.info(f'Successfully fetched balances: {balances}')
            return balances
        except (BinanceAPIException, BinanceRequestException) as e:
            logger.error(f'Error fetching Binance account balance: {e}')
            return None
        except Exception as e:
            logger.error(f'An unexpected error occurred while fetching balance: {e}')
            return None

    def get_trade_history(self, symbol=None):
        logger.info(f'Fetching trade history for symbol: {symbol if symbol else "all symbols"}')
        # Placeholder: Actual implementation will require symbol
        if not symbol:
            logger.warning('Symbol must be provided to fetch trade history.')
            return []
        try:
            trades = self.client.get_my_trades(symbol=symbol)
            logger.info(f'Successfully fetched {len(trades)} trades for {symbol}')
            return trades
        except (BinanceAPIException, BinanceRequestException) as e:
            logger.error(f'Error fetching Binance trade history for {symbol}: {e}')
            return []

    def place_order(self, symbol, side, type, quantity, price=None, test_order=False):
        logger.info(f'Placing order: {symbol}, {side}, {type}, quantity={quantity}, price={price}')
        try:
            params = {
                'symbol': symbol,
                'side': side, # Client.SIDE_BUY or Client.SIDE_SELL
                'type': type, # Client.ORDER_TYPE_LIMIT, Client.ORDER_TYPE_MARKET etc.
                'quantity': quantity
            }
            if type == Client.ORDER_TYPE_LIMIT:
                params['timeInForce'] = Client.TIME_IN_FORCE_GTC # Good Till Cancelled
                params['price'] = price

            if test_order:
                order = self.client.create_test_order(**params)
                logger.info(f'Test order placed: {order}')
            else:
                order = self.client.create_order(**params)
                logger.info(f'Order placed: {order}')
            return order
        except (BinanceAPIException, BinanceRequestException) as e:
            logger.error(f'Error placing Binance order: {e}')
            return None

    def get_market_data(self, symbol):
        logger.info(f'Fetching market data for symbol: {symbol}')
        try:
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            logger.info(f'Successfully fetched ticker for {symbol}: {ticker}')
            return ticker
        except (BinanceAPIException, BinanceRequestException) as e:
            logger.error(f'Error fetching Binance market data for {symbol}: {e}')
            return None

    def get_historical_candles(self, symbol, interval, start_str=None, end_str=None, limit=1000):
        logger.info(f'Fetching historical candles for {symbol}, interval {interval}, limit {limit}')
        try:
            candles = self.client.get_historical_klines(symbol, interval, start_str=start_str, end_str=end_str, limit=limit)
            logger.info(f'Successfully fetched {len(candles)} candles for {symbol}')
            return candles
        except (BinanceAPIException, BinanceRequestException) as e:
            logger.error(f'Error fetching Binance historical candles for {symbol}: {e}')
            return []
