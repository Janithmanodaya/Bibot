import pandas as pd
from .technical_indicators import calculate_sma, calculate_rsi, calculate_macd, calculate_bollinger_bands, calculate_stochastic_oscillator
from app.services import db_service
from binance.client import Client # For ORDER_TYPE_STOP_LOSS_LIMIT etc.
import logging
import time

logger = logging.getLogger(__name__)

class Strategy:
    def __init__(self, name, params=None):
        self.name = name
        self.params = params if params else {}
        logger.info(f'Strategy {self.name} initialized with params: {self.params}')

    def set_parameters(self, params):
        self.params.update(params)
        logger.info(f'Strategy {self.name} parameters updated: {self.params}')

    def generate_signals(self, ohlc_data: pd.DataFrame) -> str:
        raise NotImplementedError('This method should be implemented by subclasses.')

    def execute(self, ohlc_data: pd.DataFrame, exchange_service_instance, user_id=1):
        signal = self.generate_signals(ohlc_data)
        logger.info(f"Strategy {self.name} generated signal: {signal} for user {user_id} with params {self.params}")

        if signal not in ['buy', 'sell']:
            return {'status': 'hold', 'signal': signal, 'reason': 'No action signal.'}

        user_settings = db_service.get_user_setting(user_id=user_id)
        if not user_settings:
            logger.error(f"User settings not found for user_id {user_id}.")
            return {'status': 'error', 'reason': 'User settings not found.'}

        # Max Drawdown Check (New)
        peak_equity = getattr(user_settings, 'peak_account_equity', 0.0)
        if peak_equity is None: peak_equity = 0.0 # Ensure peak_equity is float if None from DB
        max_drawdown_pct = getattr(user_settings, 'max_account_drawdown_percentage', None)

        if peak_equity > 0 and max_drawdown_pct is not None and max_drawdown_pct > 0:
            logger.info(f"Performing Max Drawdown check. Peak Equity: {peak_equity}, Max Drawdown %: {max_drawdown_pct}")
            current_total_equity = exchange_service_instance.get_total_account_equity_in_usdt()
            if current_total_equity < peak_equity: # Only calculate drawdown if below peak
                current_drawdown = ((peak_equity - current_total_equity) / peak_equity) * 100
                logger.info(f"Current Equity: {current_total_equity:.2f} USDT, Current Drawdown: {current_drawdown:.2f}%")
                if current_drawdown >= float(max_drawdown_pct):
                    logger.critical(f"MAX DRAWDOWN LIMIT REACHED ({current_drawdown:.2f}% >= {max_drawdown_pct}%). Halting trades for user {user_id}.")
                    # TODO: Implement actual halting mechanism (e.g., flag in DB, global var, notification)
                    return {'status': 'error', 'reason': f'Max drawdown limit {max_drawdown_pct}% reached. Trading halted.'}
            elif current_total_equity > peak_equity:
                 # New peak equity detected, update it.
                 logger.info(f"New peak equity detected: {current_total_equity:.2f} (old: {peak_equity:.2f}). Updating user settings.")
                 # This save should ideally only update peak_equity without touching other potentially unsaved form fields.
                 # For simplicity, we pass other fields as None which save_user_setting handles by not updating them.
                 db_service.save_user_setting(user_id=user_id, peak_account_equity=current_total_equity)
                 # Note: If user is editing settings form at same time, this could overwrite.
                 # A dedicated db_service.update_peak_equity(user_id, new_peak) would be better.

        # Continue with existing execute logic
        max_trade_size_pct = getattr(user_settings, 'max_trade_size_percentage_balance', None)
        default_stop_loss_pct = getattr(user_settings, 'default_stop_loss_percentage', None)

        symbol = self.params.get('symbol', 'BTCUSDT')
        if not symbol:
            logger.error(f"Strategy {self.name} has no symbol defined."); return {'status': 'error', 'reason': 'Strategy symbol not defined.'}
        if 'close' not in ohlc_data or ohlc_data['close'].empty:
             logger.warning(f"No close prices in ohlc_data for {self.name} on {symbol}"); return {'status': 'hold', 'reason': 'Insufficient data.'}

        current_price = ohlc_data['close'].iloc[-1] # Used for checks and potentially for LIMIT order price if not specified
        entry_order_type = self.params.get('order_type', Client.ORDER_TYPE_MARKET) # Default to MARKET for entry
        entry_price_for_limit_offset_pct = self.params.get('entry_limit_price_offset_pct', 0)

        base_quantity = self.params.get('default_quantity', 0.0001)
        quantity_to_trade = base_quantity

        if signal == 'buy' and max_trade_size_pct is not None:
            account_balance_info = exchange_service_instance.get_account_balance()
            if not account_balance_info:
                logger.error(f"Could not retrieve account balance for user {user_id}."); return {'status': 'error', 'reason': 'Failed to get account balance.'}
            quote_asset = "USDT"
            if symbol.endswith("BUSD"): quote_asset = "BUSD"
            elif symbol.endswith("BTC"): quote_asset = "BTC"

            available_quote_balance = 0
            balance_asset_info = account_balance_info.get(quote_asset)
            if balance_asset_info:
                if isinstance(balance_asset_info, dict): available_quote_balance = float(balance_asset_info.get('free', 0))
                else: available_quote_balance = float(balance_asset_info or 0)

            if available_quote_balance <= 0:
                logger.warning(f"No available balance for {quote_asset}."); return {'status': 'hold', 'reason': f'Insufficient {quote_asset} balance.'}

            max_permissible_value_in_quote = available_quote_balance * (float(max_trade_size_pct) / 100.0)

            if current_price > 0: # Avoid division by zero if price is somehow zero
                quantity_allowed_by_risk = max_permissible_value_in_quote / current_price
                quantity_to_trade = min(base_quantity, quantity_allowed_by_risk)
            else:
                logger.warning(f"Current price for {symbol} is {current_price}. Cannot calculate risk-allowed quantity.");
                quantity_to_trade = 0 # Or handle as an error preventing trade

            logger.info(f"Risk check for BUY {symbol}: Max Qty: {quantity_allowed_by_risk if current_price > 0 else 'N/A'}. Final Qty: {quantity_to_trade:.6f}")

        if quantity_to_trade <= 0: # If quantity becomes zero or negative after risk check
            logger.warning(f"Quantity to trade for {symbol} is {quantity_to_trade}. Holding.")
            return {'status': 'hold', 'reason': 'Quantity to trade is zero or negative after risk checks.'}

        min_notional = self.params.get('min_notional', 10.0)
        if current_price > 0 and quantity_to_trade * current_price < min_notional: # Check current_price > 0 here too
            logger.warning(f"Order value for {symbol} below min_notional. Holding."); return {'status': 'hold', 'reason': f'Order value below min {min_notional}.'}
        elif current_price <= 0 and min_notional > 0 : # If price is zero, any trade is effectively zero notional unless min_notional is also zero
             logger.warning(f"Current price for {symbol} is {current_price}. Cannot meet min_notional {min_notional}. Holding."); return {'status': 'hold', 'reason': 'Current price is zero.'}


        entry_order_price = None
        if entry_order_type == Client.ORDER_TYPE_LIMIT:
            price_offset_multiplier = (1 - entry_price_for_limit_offset_pct / 100.0) if signal == 'buy' else (1 + entry_price_for_limit_offset_pct / 100.0)
            limit_price_candidate = current_price * price_offset_multiplier
            entry_order_price = exchange_service_instance.format_price(symbol, limit_price_candidate)


        entry_order_result = None
        stop_loss_order_result = None
        final_status = {'signal': signal, 'symbol': symbol}

        try:
            logger.info(f"Placing ENTRY order for {self.name} on {symbol}: {signal} {quantity_to_trade:.8f} Type: {entry_order_type} Price: {entry_order_price if entry_order_price else current_price:.2f}")

            formatted_quantity_to_trade = exchange_service_instance.format_quantity(symbol, quantity_to_trade)

            entry_order_result = exchange_service_instance.place_order(
                symbol=symbol, side=signal.upper(), type=entry_order_type,
                quantity=formatted_quantity_to_trade, price=entry_order_price
            )
            final_status['entry_order'] = entry_order_result
            logger.info(f"Entry order response: {entry_order_result}")

            entry_order_id = entry_order_result.get('orderId')
            entry_order_status = str(entry_order_result.get('status','')).upper()

            if entry_order_id and entry_order_status in ['NEW', 'FILLED', 'PARTIALLY_FILLED']:
                logger.info(f"Entry order for {symbol} {entry_order_status}. Proceeding to place Stop-Loss if configured.")

                if default_stop_loss_pct is not None:
                    sl_pct = float(default_stop_loss_pct)

                    # Determine actual entry price for SL calculation
                    actual_entry_price = current_price # Default to current_price
                    if entry_order_status == 'FILLED' and entry_order_result.get('fills') and len(entry_order_result['fills']) > 0:
                        actual_entry_price = float(entry_order_result['fills'][0]['price'])
                    elif entry_order_type == Client.ORDER_TYPE_LIMIT and entry_order_price: # If LIMIT order is NEW, base SL on its price
                        actual_entry_price = float(entry_order_price) # Already formatted

                    stop_loss_trigger_price = 0
                    sl_limit_price = 0

                    if signal == 'buy':
                        stop_loss_trigger_price = actual_entry_price * (1 - (sl_pct / 100.0))
                        sl_limit_price = stop_loss_trigger_price * (1 - 0.001)
                    elif signal == 'sell':
                        stop_loss_trigger_price = actual_entry_price * (1 + (sl_pct / 100.0))
                        sl_limit_price = stop_loss_trigger_price * (1 + 0.001)

                    stop_loss_trigger_price = exchange_service_instance.format_price(symbol, stop_loss_trigger_price)
                    sl_limit_price = exchange_service_instance.format_price(symbol, sl_limit_price)

                    sl_side = Client.SIDE_SELL if signal == 'buy' else Client.SIDE_BUY

                    logger.info(f"Placing STOP-LOSS order for {symbol}: Side={sl_side}, Qty={formatted_quantity_to_trade}, TriggerP={stop_loss_trigger_price}, LimitP={sl_limit_price}")
                    try:
                        if entry_order_type == Client.ORDER_TYPE_MARKET and entry_order_status != 'FILLED':
                             time.sleep(1) # Brief pause for market order to potentially fill before placing SL

                        stop_loss_order_result = exchange_service_instance.place_order(
                            symbol=symbol, side=sl_side, type=Client.ORDER_TYPE_STOP_LOSS_LIMIT,
                            quantity=formatted_quantity_to_trade, price=sl_limit_price, stop_price=stop_loss_trigger_price,
                            timeInForce=Client.TIME_IN_FORCE_GTC
                        )
                        final_status['stop_loss_order'] = stop_loss_order_result
                        logger.info(f"Stop-Loss order response: {stop_loss_order_result}")
                    except Exception as sl_e:
                        logger.error(f"Failed to place Stop-Loss order for {symbol} after entry: {sl_e}", exc_info=True)
                        final_status['stop_loss_error'] = str(sl_e)

                final_status['status'] = 'success_entry_placed'
            else:
                logger.error(f"Entry order placement failed or not confirmed: {entry_order_result}")
                final_status['status'] = 'error_entry_failed'
                final_status['reason'] = 'Entry order placement failed or status not actionable.'
                final_status['details'] = entry_order_result

        except Exception as e:
            logger.error(f"Exception during entry order placement for {self.name} on {symbol}: {e}", exc_info=True)
            final_status['status'] = 'error_exception'
            final_status['reason'] = f'Exception: {e}'

        return final_status

# --- Predefined Strategies ---
class MovingAverageCrossoverStrategy(Strategy):
    def __init__(self, params=None):
        default_params = {'short_window': 10, 'long_window': 50, 'symbol': 'BTCUSDT', 'default_quantity': 0.001, 'order_type': Client.ORDER_TYPE_MARKET}
        if params: default_params.update(params)
        super().__init__('MovingAverageCrossover', default_params)
    def generate_signals(self, ohlc_data: pd.DataFrame):
        if 'close' not in ohlc_data.columns: return 'hold'
        short_window = self.params.get('short_window'); long_window = self.params.get('long_window')
        if not (isinstance(short_window, int) and isinstance(long_window, int) and short_window > 0 and long_window > 0 and short_window < long_window): return 'hold'
        if len(ohlc_data) < long_window: return 'hold'
        short_ma = calculate_sma(ohlc_data['close'], short_window); long_ma = calculate_sma(ohlc_data['close'], long_window)
        if short_ma.empty or long_ma.empty or len(short_ma) < 1 or len(long_ma) < 1: return 'hold'
        current_short_ma = short_ma.iloc[-1]; current_long_ma = long_ma.iloc[-1]
        if current_short_ma > current_long_ma: return 'buy'
        if current_short_ma < current_long_ma: return 'sell'
        return 'hold'

class RSIOverboughtOversoldStrategy(Strategy):
    def __init__(self, params=None):
        default_params = {'rsi_window': 14, 'oversold_threshold': 30, 'overbought_threshold': 70, 'symbol': 'BTCUSDT', 'default_quantity': 0.001, 'order_type': Client.ORDER_TYPE_MARKET}
        if params: default_params.update(params)
        super().__init__('RSIOverboughtOversold', default_params)
    def generate_signals(self, ohlc_data: pd.DataFrame):
        if 'close' not in ohlc_data.columns: return 'hold'
        rsi_window = self.params.get('rsi_window', 14); oversold_threshold = self.params.get('oversold_threshold', 30); overbought_threshold = self.params.get('overbought_threshold', 70)
        if not (isinstance(rsi_window, int) and rsi_window > 0): return 'hold'
        if len(ohlc_data) < rsi_window + 1: return 'hold'
        rsi = calculate_rsi(ohlc_data['close'], rsi_window)
        if rsi.empty or len(rsi) < 1: return 'hold'
        current_rsi = rsi.iloc[-1]
        if current_rsi < oversold_threshold: return 'buy'
        if current_rsi > overbought_threshold: return 'sell'
        return 'hold'

class MACDSignalStrategy(Strategy):
    def __init__(self, params=None):
        default_params = {'short_window': 12, 'long_window': 26, 'signal_window': 9, 'symbol': 'BTCUSDT', 'default_quantity': 0.001, 'order_type': Client.ORDER_TYPE_MARKET}
        if params: default_params.update(params)
        super().__init__('MACDSignal', default_params)
    def generate_signals(self, ohlc_data: pd.DataFrame):
        if 'close' not in ohlc_data.columns: return 'hold'
        short_w = self.params.get('short_window', 12); long_w = self.params.get('long_window', 26); signal_w = self.params.get('signal_window', 9)
        if not (isinstance(short_w,int) and isinstance(long_w,int) and isinstance(signal_w,int) and short_w > 0 and long_w > 0 and signal_w > 0 and long_w > short_w): return 'hold'
        if len(ohlc_data) < long_w + signal_w: return 'hold'
        macd_line, signal_line, _ = calculate_macd(ohlc_data['close'], short_w, long_w, signal_w)
        if macd_line.empty or signal_line.empty or len(macd_line) < 1 or len(signal_line) < 1: return 'hold'
        current_macd = macd_line.iloc[-1]; current_signal = signal_line.iloc[-1]
        if current_macd > current_signal: return 'buy'
        if current_macd < current_signal: return 'sell'
        return 'hold'

class BollingerBandsStrategy(Strategy):
    def __init__(self, params=None):
        default_params = {'bb_window': 20, 'bb_std_dev': 2, 'symbol': 'BTCUSDT', 'default_quantity': 0.001, 'order_type': Client.ORDER_TYPE_MARKET}
        if params: default_params.update(params)
        super().__init__('BollingerBands', default_params)
    def generate_signals(self, ohlc_data: pd.DataFrame):
        if 'close' not in ohlc_data.columns: return 'hold'
        window = self.params.get('bb_window', 20); num_std_dev = self.params.get('bb_std_dev', 2)
        if not (isinstance(window, int) and window > 0 and isinstance(num_std_dev, (int,float)) and num_std_dev > 0): return 'hold'
        if len(ohlc_data) < window: return 'hold'
        upper_band, _, lower_band = calculate_bollinger_bands(ohlc_data['close'], window, num_std_dev)
        if upper_band.empty or lower_band.empty or len(upper_band) < 1 or len(lower_band) < 1: return 'hold'
        current_close = ohlc_data['close'].iloc[-1]; current_lower_band = lower_band.iloc[-1]; current_upper_band = upper_band.iloc[-1]
        if current_close <= current_lower_band: return 'buy'
        if current_close >= current_upper_band: return 'sell'
        return 'hold'

class StochasticOscillatorStrategy(Strategy):
    def __init__(self, params=None):
        default_params = {'k_window': 14, 'd_window': 3, 'oversold_level': 20, 'overbought_level': 80, 'symbol': 'BTCUSDT', 'default_quantity': 0.001, 'order_type': Client.ORDER_TYPE_MARKET}
        if params: default_params.update(params)
        super().__init__('StochasticOscillator', default_params)
    def generate_signals(self, ohlc_data: pd.DataFrame):
        req_cols = ['high', 'low', 'close'];
        if not all(col in ohlc_data.columns for col in req_cols): return 'hold'
        k_w = self.params.get('k_window', 14); d_w = self.params.get('d_window', 3); ovs_lvl = self.params.get('oversold_level', 20); ovb_lvl = self.params.get('overbought_level', 80)
        if not (isinstance(k_w,int) and k_w > 0 and isinstance(d_w,int) and d_w > 0): return 'hold'
        if len(ohlc_data) < k_w : return 'hold'
        percent_k, _ = calculate_stochastic_oscillator(ohlc_data['high'], ohlc_data['low'], ohlc_data['close'], k_w, d_w)
        if percent_k.empty or len(percent_k) < 1: return 'hold'
        current_k = percent_k.iloc[-1]
        if current_k < ovs_lvl: return 'buy'
        if current_k > ovb_lvl: return 'sell'
        return 'hold'
