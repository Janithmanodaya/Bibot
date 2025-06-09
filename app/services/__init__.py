# This file makes the 'services' directory a Python package
from .exchange_service import ExchangeService
from .binance_service import BinanceService
from .db_service import get_user_setting, save_user_setting, add_trade_history, store_ohlc_data

# Imports for Strategy and Technical Indicators
from .strategy_service import Strategy
from . import technical_indicators

from .risk_management_service import RiskManager

# Predefined strategy classes for easier access
from .strategy_service import MovingAverageCrossoverStrategy, RSIOverboughtOversoldStrategy, MACDSignalStrategy, BollingerBandsStrategy, StochasticOscillatorStrategy
