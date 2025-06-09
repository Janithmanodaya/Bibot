from .exchange_service import ExchangeService
from binance.client import Client # Corrected imports
from binance.exceptions import BinanceAPIException, BinanceRequestException
import logging

logger = logging.getLogger(__name__)

class BinanceService(ExchangeService):
    _symbol_info_cache = {} # Class level cache for symbol info

    def _get_symbol_info(self, symbol):
        if symbol in self._symbol_info_cache: # Use self._symbol_info_cache
            return self._symbol_info_cache[symbol]
        try:
            info = self.client.get_symbol_info(symbol)
            if info:
                self._symbol_info_cache[symbol] = info
                return info
            logger.error(f"Could not retrieve symbol info for {symbol}")
            return None
        except Exception as e:
            logger.error(f"Exception fetching symbol info for {symbol}: {e}")
            return None

    def format_price(self, symbol, price):
        info = self._get_symbol_info(symbol)
        if not info: return f"{float(price):.8f}" # Fallback, 8 decimals

        for f_filter in info.get('filters', []):
            if f_filter['filterType'] == 'PRICE_FILTER':
                tick_size_str = f_filter['tickSize']
                tick_size = float(tick_size_str)

                if '.' in tick_size_str:
                    precision = len(tick_size_str.split('.')[1].rstrip('0'))
                else:
                    precision = 0

                # Apply tick_size: price = floor(price / tick_size) * tick_size (usually for quote asset, not always directly applicable like this for formatting)
                # For formatting to precision:
                return f"{float(price):.{precision}f}"
        return f"{float(price):.8f}"

    def format_quantity(self, symbol, quantity):
        info = self._get_symbol_info(symbol)
        if not info: return f"{float(quantity):.8f}" # Fallback

        for f_filter in info.get('filters', []):
            if f_filter['filterType'] == 'LOT_SIZE':
                step_size_str = f_filter['stepSize']
                step_size = float(step_size_str)
                min_qty = float(f_filter['minQty'])
                # max_qty = float(f_filter['maxQty']) # Not used in this formatting logic directly

                # Ensure quantity meets minQty (though actual order placement might fail if below)
                # quantity = max(float(quantity), min_qty)

                if '.' in step_size_str:
                    precision = len(step_size_str.split('.')[1].rstrip('0'))
                else:
                    precision = 0

                # Adjust quantity to be a multiple of step_size by flooring
                quantity = (float(quantity) // step_size) * step_size
                return f"{quantity:.{precision}f}"
        return f"{float(quantity):.8f}"

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

    def place_order(self, symbol, side, type, quantity, price=None, stop_price=None, test_order=False):
        logger.info(f'Placing order: {symbol}, {side}, {type}, Qty:{quantity}, P:{price}, SP:{stop_price}, Test:{test_order}')
        try:
            # Dynamically import Client constants ONLY if needed inside method, or ensure they are class/module level
            # For simplicity, assuming Client is available as self.client which has these constants.
            # e.g. self.client.ORDER_TYPE_LIMIT

            params = {
                'symbol': symbol,
                'side': side,
                'type': type,
                'quantity': self.format_quantity(symbol, quantity)
            }

            if type == self.client.ORDER_TYPE_LIMIT or \
               type == self.client.ORDER_TYPE_STOP_LOSS_LIMIT or \
               type == self.client.ORDER_TYPE_TAKE_PROFIT_LIMIT:
                if not price:
                    logger.error(f"Price must be provided for order type {type}")
                    raise ValueError(f"Price is required for order type {type}")
                params['price'] = self.format_price(symbol, price)
                params['timeInForce'] = self.client.TIME_IN_FORCE_GTC

            if type == self.client.ORDER_TYPE_LIMIT_MAKER:
                if not price:
                    raise ValueError(f"Price is required for order type {type}")
                params['price'] = self.format_price(symbol, price)

            if stop_price and (type == self.client.ORDER_TYPE_STOP_LOSS or \
                               type == self.client.ORDER_TYPE_STOP_LOSS_LIMIT or \
                               type == self.client.ORDER_TYPE_TAKE_PROFIT or \
                               type == self.client.ORDER_TYPE_TAKE_PROFIT_LIMIT):
                params['stopPrice'] = self.format_price(symbol, stop_price)

            # If it's a STOP_LOSS or TAKE_PROFIT (market) order, it only needs stopPrice, not price or timeInForce.
            if type == self.client.ORDER_TYPE_STOP_LOSS or type == self.client.ORDER_TYPE_TAKE_PROFIT:
                if 'price' in params: del params['price']
                if 'timeInForce' in params: del params['timeInForce']


            logger.debug(f"Order params for Binance: {params}")

            if test_order:
                # Note: create_test_order might not support all complex order types or params.
                # It's primarily for validating connectivity and basic order structure.
                logger.info(f"Submitting TEST order with params: {params}")
                order = self.client.create_test_order(**params)
                logger.info(f'Test order placed successfully: {order}')
            else:
                logger.info(f"Submitting REAL order with params: {params}")
                order = self.client.create_order(**params)
                logger.info(f'Order placed successfully: {order}')
            return order
        except BinanceAPIException as e:
            logger.error(f'Binance API Exception placing order for {symbol}: {e}')
            raise # Re-raise to be caught by caller if needed
        except BinanceRequestException as e:
            logger.error(f'Binance Request Exception placing order for {symbol}: {e}')
            raise
        except Exception as e:
            logger.error(f'Unexpected error placing order for {symbol}: {e}', exc_info=True)
            raise

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

    def get_order(self, symbol, order_id):
        logger.info(f'Fetching order {order_id} for symbol {symbol}')
        try:
            order = self.client.get_order(symbol=symbol, orderId=order_id)
            logger.info(f'Successfully fetched order {order_id} for {symbol}: {order}')
            return order
        except (BinanceAPIException, BinanceRequestException) as e:
            logger.error(f'Error fetching Binance order {order_id} for {symbol}: {e}')
            return None

    def cancel_order(self, symbol, order_id):
        logger.info(f'Cancelling order {order_id} for symbol {symbol}')
        try:
            result = self.client.cancel_order(symbol=symbol, orderId=order_id)
            logger.info(f'Successfully cancelled order {order_id} for {symbol}: {result}')
            return result
        except (BinanceAPIException, BinanceRequestException) as e:
            logger.error(f'Error cancelling Binance order {order_id} for {symbol}: {e}')
            return None

    def get_open_orders(self, symbol=None):
        logger.info(f'Fetching open orders for symbol: {symbol if symbol else "all symbols"}')
        try:
            open_orders = self.client.get_open_orders(symbol=symbol) if symbol else self.client.get_open_orders()
            logger.info(f'Successfully fetched {len(open_orders)} open orders for {symbol if symbol else "all symbols"}')
            return open_orders
        except (BinanceAPIException, BinanceRequestException) as e:
            logger.error(f'Error fetching Binance open orders for {symbol if symbol else "all symbols"}: {e}')
            return []
