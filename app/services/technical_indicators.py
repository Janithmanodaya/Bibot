import pandas as pd
import logging

logger = logging.getLogger(__name__)

def calculate_sma(data: pd.Series, window: int) -> pd.Series:
    logger.info(f'Calculating SMA with window {window}')
    if window <= 0:
        logger.error('SMA window must be positive')
        return pd.Series(dtype='float64')
    if len(data) < window:
        logger.warning(f'Data length ({len(data)}) is less than SMA window ({window}). Returning empty series.')
        return pd.Series(dtype='float64')
    return data.rolling(window=window).mean()

def calculate_ema(data: pd.Series, window: int) -> pd.Series:
    logger.info(f'Calculating EMA with window {window}')
    if window <= 0:
        logger.error('EMA window must be positive')
        return pd.Series(dtype='float64')
    if len(data) < window:
        logger.warning(f'Data length ({len(data)}) is less than EMA window ({window}). Returning empty series.')
        return pd.Series(dtype='float64')
    return data.ewm(span=window, adjust=False).mean()

def calculate_rsi(data: pd.Series, window: int = 14) -> pd.Series:
    logger.info(f'Calculating RSI with window {window}')
    if window <= 0:
        logger.error('RSI window must be positive')
        return pd.Series(dtype='float64')
    if len(data) < window + 1: # RSI needs at least window + 1 data points for proper calculation
        logger.warning(f'Data length ({len(data)}) is less than RSI window+1 ({window+1}). Returning empty series.')
        return pd.Series(dtype='float64')
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_macd(data: pd.Series, short_window: int = 12, long_window: int = 26, signal_window: int = 9) -> tuple[pd.Series, pd.Series, pd.Series]:
    logger.info(f'Calculating MACD with short_window={short_window}, long_window={long_window}, signal_window={signal_window}')
    if not (short_window > 0 and long_window > 0 and signal_window > 0 and long_window > short_window):
        logger.error('Invalid MACD window parameters')
        return pd.Series(dtype='float64'), pd.Series(dtype='float64'), pd.Series(dtype='float64')
    short_ema = calculate_ema(data, short_window)
    long_ema = calculate_ema(data, long_window)
    macd_line = short_ema - long_ema
    signal_line = calculate_ema(macd_line, signal_window)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def calculate_bollinger_bands(data: pd.Series, window: int = 20, num_std_dev: int = 2) -> tuple[pd.Series, pd.Series, pd.Series]:
    logger.info(f'Calculating Bollinger Bands with window={window}, num_std_dev={num_std_dev}')
    if window <= 0 or num_std_dev <=0:
        logger.error('Bollinger Bands window and num_std_dev must be positive')
        return pd.Series(dtype='float64'), pd.Series(dtype='float64'), pd.Series(dtype='float64')
    sma = calculate_sma(data, window)
    rolling_std = data.rolling(window=window).std()
    upper_band = sma + (rolling_std * num_std_dev)
    lower_band = sma - (rolling_std * num_std_dev)
    return upper_band, sma, lower_band # Upper, Middle, Lower

def calculate_stochastic_oscillator(high: pd.Series, low: pd.Series, close: pd.Series, k_window: int = 14, d_window: int = 3) -> tuple[pd.Series, pd.Series]:
    logger.info(f'Calculating Stochastic Oscillator with K_window={k_window}, D_window={d_window}')
    if not (k_window > 0 and d_window > 0):
        logger.error('Stochastic Oscillator K and D windows must be positive')
        return pd.Series(dtype='float64'), pd.Series(dtype='float64')
    lowest_low = low.rolling(window=k_window).min()
    highest_high = high.rolling(window=k_window).max()
    percent_k = ((close - lowest_low) / (highest_high - lowest_low)) * 100
    percent_d = calculate_sma(percent_k, d_window)
    return percent_k, percent_d
