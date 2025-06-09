import pandas as pd
# Ensure all necessary technical indicator functions are imported
from .technical_indicators import (
    calculate_sma,
    calculate_rsi,
    calculate_macd,
    calculate_bollinger_bands,
    calculate_stochastic_oscillator
)
import logging

logger = logging.getLogger(__name__)

class Strategy:
    def __init__(self, name, params=None):
        self.name = name
        self.params = params if params else {}
        logger.info(f'Strategy {self.name} initialized with params: {self.params}')

    def set_parameters(self, params):
        self.params.update(params)
        logger.info(f'Strategy {self.name} parameters updated: {self.params}')

    def generate_signals(self, ohlc_data: pd.DataFrame):
        """
        Generates trading signals based on the OHLC data.
        :param ohlc_data: Pandas DataFrame with columns ['open_time', 'open', 'high', 'low', 'close', 'volume']
        :return: A signal ('buy', 'sell', 'hold') or a more complex signal object.
        """
        raise NotImplementedError('This method should be implemented by subclasses.')

    def execute(self, current_market_data, account_balance, open_positions):
        """
        Makes a decision to trade based on generated signals and current market conditions.
        This might involve risk management checks before placing an order.
        """
        # signals = self.generate_signals(current_market_data) # Assuming current_market_data is sufficient or historical is pre-loaded
        # Decision logic here
        logger.warning(f'Execution logic for strategy {self.name} not implemented.')
        return None # No action

# --- Predefined Strategies ---

class MovingAverageCrossoverStrategy(Strategy):
    def __init__(self, params=None):
        # Adjusted default_params
        default_params = {'short_window': 10, 'long_window': 50}
        if params: default_params.update(params)
        super().__init__('MovingAverageCrossover', default_params)

    def generate_signals(self, ohlc_data: pd.DataFrame):
        logger.info(f'{self.name}: Generating signals with params {self.params} using simplified logic.')
        if 'close' not in ohlc_data.columns:
            logger.error(f'{self.name}: OHLC data must contain a "close" column.')
            return 'hold'

        short_window = self.params.get('short_window')
        long_window = self.params.get('long_window')

        if not (isinstance(short_window, int) and isinstance(long_window, int) and short_window > 0 and long_window > 0 and short_window < long_window):
            logger.error(f'{self.name}: Invalid MA windows: short={short_window}, long={long_window}')
            return 'hold'

        if len(ohlc_data) < long_window:
            logger.warning(f'{self.name}: Data length ({len(ohlc_data)}) is less than long_window ({long_window}). Cannot generate reliable signal.')
            return 'hold'

        short_ma = calculate_sma(ohlc_data['close'], short_window)
        long_ma = calculate_sma(ohlc_data['close'], long_window)

        if short_ma.empty or long_ma.empty or len(short_ma) < 1 or len(long_ma) < 1: # Ensure MAs are not empty
            return 'hold'

        current_short_ma = short_ma.iloc[-1]
        current_long_ma = long_ma.iloc[-1]

        # Simplified logic (no crossover condition)
        if current_short_ma > current_long_ma:
            logger.info(f'{self.name}: Buy signal generated (Short MA > Long MA).')
            return 'buy'
        if current_short_ma < current_long_ma:
            logger.info(f'{self.name}: Sell signal generated (Short MA < Long MA).')
            return 'sell'

        return 'hold'

class RSIOverboughtOversoldStrategy(Strategy):
    def __init__(self, params=None):
        # Default params match specification
        default_params = {'rsi_window': 14, 'oversold_threshold': 30, 'overbought_threshold': 70}
        if params: default_params.update(params)
        super().__init__('RSIOverboughtOversold', default_params)

    def generate_signals(self, ohlc_data: pd.DataFrame): # Logic remains the same as previous step
        logger.info(f'{self.name}: Generating signals with params {self.params}')
        if 'close' not in ohlc_data.columns:
            logger.error(f'{self.name}: OHLC data must contain a "close" column.')
            return 'hold'

        rsi_window = self.params.get('rsi_window', 14)
        oversold_threshold = self.params.get('oversold_threshold', 30)
        overbought_threshold = self.params.get('overbought_threshold', 70)

        if not (isinstance(rsi_window, int) and rsi_window > 0):
            logger.error(f'{self.name}: Invalid RSI window: {rsi_window}')
            return 'hold'
        if len(ohlc_data) < rsi_window + 1:
            logger.warning(f'{self.name}: Data length ({len(ohlc_data)}) insufficient for RSI window {rsi_window}.')
            return 'hold'

        rsi = calculate_rsi(ohlc_data['close'], rsi_window)

        if rsi.empty or len(rsi) < 1:
            return 'hold'

        current_rsi = rsi.iloc[-1]

        if current_rsi < oversold_threshold:
            logger.info(f'{self.name}: Buy signal generated (RSI {current_rsi:.2f} < {oversold_threshold}).')
            return 'buy'
        if current_rsi > overbought_threshold:
            logger.info(f'{self.name}: Sell signal generated (RSI {current_rsi:.2f} > {overbought_threshold}).')
            return 'sell'

        return 'hold'

class MACDSignalStrategy(Strategy):
    def __init__(self, params=None):
        # Default params match specification
        default_params = {'short_window': 12, 'long_window': 26, 'signal_window': 9}
        if params: default_params.update(params)
        super().__init__('MACDSignal', default_params)

    def generate_signals(self, ohlc_data: pd.DataFrame):
        logger.info(f'{self.name}: Generating signals with params {self.params} using simplified logic.')
        if 'close' not in ohlc_data.columns:
            logger.error(f'{self.name}: OHLC data must contain a "close" column.')
            return 'hold'

        short_window = self.params.get('short_window', 12)
        long_window = self.params.get('long_window', 26)
        signal_window = self.params.get('signal_window', 9)

        if not (isinstance(short_window,int) and isinstance(long_window,int) and isinstance(signal_window,int) and \
                short_window > 0 and long_window > 0 and signal_window > 0 and long_window > short_window):
            logger.error(f'{self.name}: Invalid MACD parameters.')
            return 'hold'

        if len(ohlc_data) < long_window + signal_window:
             logger.warning(f'{self.name}: Data length ({len(ohlc_data)}) insufficient for MACD calc.')
             return 'hold'

        macd_line, signal_line, _ = calculate_macd(ohlc_data['close'], short_window, long_window, signal_window)

        if macd_line.empty or signal_line.empty or len(macd_line) < 1 or len(signal_line) < 1:
            return 'hold'

        current_macd = macd_line.iloc[-1]
        current_signal = signal_line.iloc[-1]

        # Simplified logic (no crossover condition)
        if current_macd > current_signal:
            logger.info(f'{self.name}: Buy signal generated (MACD Line > Signal Line).')
            return 'buy'
        if current_macd < current_signal:
            logger.info(f'{self.name}: Sell signal generated (MACD Line < Signal Line).')
            return 'sell'

        return 'hold'

class BollingerBandsStrategy(Strategy):
    def __init__(self, params=None):
        # Default params match specification
        default_params = {'bb_window': 20, 'bb_std_dev': 2}
        if params: default_params.update(params)
        super().__init__('BollingerBands', default_params)

    def generate_signals(self, ohlc_data: pd.DataFrame): # Logic remains the same as previous step
        logger.info(f'{self.name}: Generating signals with params {self.params}')
        if 'close' not in ohlc_data.columns:
            logger.error(f'{self.name}: OHLC data must contain a "close" column.')
            return 'hold'

        window = self.params.get('bb_window', 20)
        num_std_dev = self.params.get('bb_std_dev', 2)

        if not (isinstance(window, int) and window > 0 and isinstance(num_std_dev, (int,float)) and num_std_dev > 0):
            logger.error(f'{self.name}: Invalid Bollinger Bands parameters.')
            return 'hold'

        if len(ohlc_data) < window:
            logger.warning(f'{self.name}: Data length ({len(ohlc_data)}) insufficient for BB window {window}.')
            return 'hold'

        upper_band, _, lower_band = calculate_bollinger_bands(ohlc_data['close'], window, num_std_dev)

        if upper_band.empty or lower_band.empty or len(upper_band) < 1 or len(lower_band) < 1:
            return 'hold'

        current_close = ohlc_data['close'].iloc[-1]
        current_lower_band = lower_band.iloc[-1]
        current_upper_band = upper_band.iloc[-1]

        if current_close <= current_lower_band:
            logger.info(f'{self.name}: Buy signal generated (Price <= Lower BB).')
            return 'buy'
        if current_close >= current_upper_band:
            logger.info(f'{self.name}: Sell signal generated (Price >= Upper BB).')
            return 'sell'

        return 'hold'

class StochasticOscillatorStrategy(Strategy):
    def __init__(self, params=None):
        # Adjusted default_params keys
        default_params = {'k_window': 14, 'd_window': 3, 'oversold_level': 20, 'overbought_level': 80}
        if params: default_params.update(params)
        super().__init__('StochasticOscillator', default_params)

    def generate_signals(self, ohlc_data: pd.DataFrame):
        logger.info(f'{self.name}: Generating signals with params {self.params} using simplified logic.')
        required_cols = ['high', 'low', 'close']
        if not all(col in ohlc_data.columns for col in required_cols):
            logger.error(f'{self.name}: OHLC data must contain "high", "low", and "close" columns.')
            return 'hold'

        k_window = self.params.get('k_window', 14)
        d_window = self.params.get('d_window', 3) # %D is calculated but not used in this simplified logic
        oversold_level = self.params.get('oversold_level', 20) # Adjusted key
        overbought_level = self.params.get('overbought_level', 80) # Adjusted key


        if not (isinstance(k_window,int) and k_window > 0 and isinstance(d_window,int) and d_window > 0):
            logger.error(f'{self.name}: Invalid Stochastic Oscillator parameters.')
            return 'hold'

        if len(ohlc_data) < k_window :
             logger.warning(f'{self.name}: Data length ({len(ohlc_data)}) insufficient for Stoch %K calc.')
             return 'hold'

        # %D (percent_d) is calculated by calculate_stochastic_oscillator but not used in this simplified logic
        percent_k, _ = calculate_stochastic_oscillator(ohlc_data['high'], ohlc_data['low'], ohlc_data['close'], k_window, d_window)

        if percent_k.empty or len(percent_k) < 1:
            return 'hold'

        current_k = percent_k.iloc[-1]

        # Simplified logic using only %K and levels
        if current_k < oversold_level:
            logger.info(f'{self.name}: Buy signal generated (Stochastic %K < {oversold_level}).')
            return 'buy'
        if current_k > overbought_level:
            logger.info(f'{self.name}: Sell signal generated (Stochastic %K > {overbought_level}).')
            return 'sell'

        return 'hold'
