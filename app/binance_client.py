from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceOrderException

# Helper function to initialize Binance client
def _get_binance_client(api_key, api_secret):
    return Client(api_key, api_secret)

# Fetch account balance
def get_account_balance(api_key, api_secret):
    try:
        client = _get_binance_client(api_key, api_secret)
        account_info = client.get_account()
        balances = [bal for bal in account_info['balances'] if float(bal['free']) > 0 or float(bal['locked']) > 0]
        return balances
    except BinanceAPIException as e:
        print(f"Binance API Exception: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred in get_account_balance: {e}")
        return None

# Fetch trade history for a specific symbol
def get_trade_history(api_key, api_secret, symbol):
    try:
        client = _get_binance_client(api_key, api_secret)
        trades = client.get_my_trades(symbol=symbol)
        return trades
    except BinanceAPIException as e:
        print(f"Binance API Exception: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred in get_trade_history: {e}")
        return None

# Place a market order
def place_market_order(api_key, api_secret, symbol, side, quantity):
    try:
        client = _get_binance_client(api_key, api_secret)
        if isinstance(side, str):
            side_enum = Client.SIDE_BUY if side.upper() == 'BUY' else Client.SIDE_SELL
        else:
            side_enum = side

        order = client.create_order(
            symbol=symbol,
            side=side_enum,
            type=Client.ORDER_TYPE_MARKET,
            quantity=quantity
        )
        return order
    except BinanceAPIException as e:
        print(f"Binance API Exception: {e}")
        return None
    except BinanceOrderException as e:
        print(f"Binance Order Exception: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred in place_market_order: {e}")
        return None

# Place a limit order
def place_limit_order(api_key, api_secret, symbol, side, quantity, price):
    try:
        client = _get_binance_client(api_key, api_secret)
        if isinstance(side, str):
            side_enum = Client.SIDE_BUY if side.upper() == 'BUY' else Client.SIDE_SELL
        else:
            side_enum = side

        order = client.create_order(
            symbol=symbol,
            side=side_enum,
            type=Client.ORDER_TYPE_LIMIT,
            timeInForce=Client.TIME_IN_FORCE_GTC,  # Good Till Canceled
            quantity=quantity,
            price=f'{price:.8f}' # Ensure price is formatted correctly
        )
        return order
    except BinanceAPIException as e:
        print(f"Binance API Exception: {e}")
        return None
    except BinanceOrderException as e:
        print(f"Binance Order Exception: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred in place_limit_order: {e}")
        return None

# Cancel an order
def cancel_order(api_key, api_secret, symbol, order_id):
    try:
        client = _get_binance_client(api_key, api_secret)
        result = client.cancel_order(
            symbol=symbol,
            orderId=order_id
        )
        return result
    except BinanceAPIException as e:
        print(f"Binance API Exception: {e}")
        return None
    except BinanceOrderException as e:
        print(f"Binance Order Exception: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred in cancel_order: {e}")
        return None

# Get symbol information
def get_symbol_info(api_key, api_secret, symbol):
    try:
        client = _get_binance_client(api_key, api_secret)
        info = client.get_symbol_info(symbol)
        return info
    except BinanceAPIException as e:
        print(f"Binance API Exception: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred in get_symbol_info: {e}")
        return None

# Get current ticker price for a symbol
def get_ticker_price(api_key, api_secret, symbol):
    try:
        client = _get_binance_client(api_key, api_secret)
        ticker = client.get_symbol_ticker(symbol=symbol)
        return ticker['price']
    except BinanceAPIException as e:
        print(f"Binance API Exception: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred in get_ticker_price: {e}")
        return None

if __name__ == '__main__':
    # This part is for testing and will require actual API keys and a symbol like 'BTCUSDT'
    # Replace with your actual API_KEY and API_SECRET for testing
    # Be cautious with real keys and real orders.
    print("Binance client functions defined. Run with API keys to test.")
    # Example (requires valid API keys and symbol):
    # api_key = "YOUR_API_KEY"
    # api_secret = "YOUR_API_SECRET"
    # symbol_to_test = "BTCUSDT" # Or any other valid symbol on your exchange

    # if api_key != "YOUR_API_KEY" and api_secret != "YOUR_API_SECRET":
    #     print(f"Testing with symbol: {symbol_to_test}")

    #     balance = get_account_balance(api_key, api_secret)
    #     if balance:
    #         print("\nAccount Balance:")
    #         for item in balance:
    #             print(f"  {item['asset']}: Free: {item['free']}, Locked: {item['locked']}")

    #     trades = get_trade_history(api_key, api_secret, symbol_to_test)
    #     if trades:
    #         print(f"\nTrade History for {symbol_to_test}: (last {len(trades)} trades)")
    #         for trade in trades[:5]: # Print first 5 trades
    #             print(f"  ID: {trade['id']}, Price: {trade['price']}, Qty: {trade['qty']}, Time: {trade['time']}")

    #     symbol_info = get_symbol_info(api_key, api_secret, symbol_to_test)
    #     if symbol_info:
    #         print(f"\nSymbol Info for {symbol_to_test}:")
    #         print(f"  Status: {symbol_info['status']}")
    #         print(f"  Base Asset: {symbol_info['baseAsset']}")
    #         print(f"  Quote Asset: {symbol_info['quoteAsset']}")
    #         for f in symbol_info['filters']:
    #             if f['filterType'] == 'LOT_SIZE':
    #                 print(f"  Min Quantity (LOT_SIZE): {f['minQty']}")
    #                 print(f"  Max Quantity (LOT_SIZE): {f['maxQty']}")
    #                 print(f"  Step Size (LOT_SIZE): {f['stepSize']}")
    #             if f['filterType'] == 'PRICE_FILTER':
    #                 print(f"  Min Price (PRICE_FILTER): {f['minPrice']}")
    #                 print(f"  Max Price (PRICE_FILTER): {f['maxPrice']}")
    #                 print(f"  Tick Size (PRICE_FILTER): {f['tickSize']}")


    #     ticker_price = get_ticker_price(api_key, api_secret, symbol_to_test)
    #     if ticker_price:
    #         print(f"\nCurrent Ticker Price for {symbol_to_test}: {ticker_price}")

        # Example: Placing a TEST MARKET BUY order (use with extreme caution, ideally on testnet)
        # Ensure the symbol allows market orders and you have sufficient balance.
        # This is commented out by default to prevent accidental real orders.
        # min_qty_info = next((f for f in symbol_info['filters'] if f['filterType'] == 'LOT_SIZE'), None)
        # if min_qty_info:
        #     min_permissible_qty = float(min_qty_info['minQty'])
        #     print(f"Minimum permissible quantity for {symbol_to_test} is {min_permissible_qty}")
        #     # market_buy_order = place_market_order(api_key, api_secret, symbol_to_test, "BUY", min_permissible_qty)
        #     # if market_buy_order:
        #     #     print("\nMarket Buy Order Response:")
        #     #     print(market_buy_order)

        # Example: Placing a TEST LIMIT BUY order (use with extreme caution, ideally on testnet)
        # current_price_float = float(ticker_price)
        # limit_buy_price = current_price_float * 0.98 # 2% below current price
        # if min_qty_info and ticker_price:
        #     limit_order_qty = float(min_qty_info['minQty'])
        #     # limit_buy_order = place_limit_order(api_key, api_secret, symbol_to_test, "BUY", limit_order_qty, limit_buy_price)
        #     # if limit_buy_order:
        #     #     print("\nLimit Buy Order Response:")
        #     #     print(limit_buy_order)
        #     #     # Example: Cancel the order just placed (if it wasn't immediately filled)
        #     #     if limit_buy_order.get('orderId'):
        #     #         time.sleep(2) # Give it a moment
        #     #         cancel_response = cancel_order(api_key, api_secret, symbol_to_test, limit_buy_order['orderId'])
        #     #         if cancel_response:
        #     #             print("\nCancel Order Response:")
        #     #             print(cancel_response)
    # else:
    #     print("Please replace 'YOUR_API_KEY' and 'YOUR_API_SECRET' with actual keys to run test calls.")
    #     print("Ensure the symbol is also correctly set for your exchange (e.g., BTCUSDT, ETHUSDT).")
    pass
