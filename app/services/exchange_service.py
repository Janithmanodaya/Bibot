class ExchangeService:
    def __init__(self, api_key, api_secret):
        self.api_key = api_key
        self.api_secret = api_secret

    def get_account_balance(self):
        raise NotImplementedError

    def get_trade_history(self, symbol=None):
        raise NotImplementedError

    def place_order(self, symbol, side, type, quantity, price=None):
        raise NotImplementedError

    def get_market_data(self, symbol):
        raise NotImplementedError

    def get_historical_candles(self, symbol, interval, limit=1000):
        raise NotImplementedError
