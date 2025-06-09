import logging

logger = logging.getLogger(__name__)

class RiskManager:
    def __init__(self, user_settings=None):
        """
        Initializes the RiskManager.
        :param user_settings: Optional dictionary or object containing user-defined risk parameters.
        """
        self.settings = user_settings if user_settings else {}
        # Default risk parameters can be set here or loaded from settings
        self.max_drawdown_pct = self.settings.get('max_drawdown_pct', 0.10)  # 10% default
        self.risk_per_trade_pct = self.settings.get('risk_per_trade_pct', 0.01)  # 1% default
        logger.info(f'RiskManager initialized with settings: {self.settings}')

    def check_max_drawdown(self, current_equity, initial_equity):
        """
        Checks if the maximum drawdown limit has been exceeded.
        :param current_equity: The current total equity of the account.
        :param initial_equity: The initial equity or equity at the start of a period.
        :return: True if drawdown is within limits, False otherwise.
        """
        if initial_equity <= 0:
            logger.warning('Initial equity is zero or negative, cannot calculate drawdown.')
            return True # Or handle as an error
        drawdown = (initial_equity - current_equity) / initial_equity
        logger.info(f'Current drawdown: {drawdown:.2%}, Max allowed: {self.max_drawdown_pct:.2%}')
        if drawdown > self.max_drawdown_pct:
            logger.warning(f'Maximum drawdown exceeded: {drawdown:.2%} > {self.max_drawdown_pct:.2%}')
            return False
        return True

    def calculate_trade_size(self, account_balance, entry_price, stop_loss_price=None):
        """
        Calculates the trade size based on account balance and risk per trade percentage.
        If stop_loss_price is provided, it calculates size based on potential loss.
        :param account_balance: Current account balance.
        :param entry_price: The price at which the trade will be entered.
        :param stop_loss_price: Optional. The price at which the trade will be stopped out.
        :return: The calculated trade size (e.g., number of units/shares/contracts).
        """
        amount_to_risk = account_balance * self.risk_per_trade_pct
        if stop_loss_price is not None and entry_price != stop_loss_price:
            risk_per_unit = abs(entry_price - stop_loss_price)
            if risk_per_unit == 0: # Should not happen if entry_price != stop_loss_price
                logger.warning('Risk per unit is zero, cannot calculate trade size based on stop loss.')
                # Fallback to simpler sizing or return 0
                trade_size = (amount_to_risk / entry_price) if entry_price > 0 else 0
            else:
                trade_size = amount_to_risk / risk_per_unit
        elif entry_price > 0:
            # Fallback if no SL price provided, size as a fraction of balance at current price
            trade_size = amount_to_risk / entry_price
        else:
            logger.warning('Entry price is zero or negative, cannot calculate trade size.')
            trade_size = 0
        logger.info(f'Calculated trade size: {trade_size} units, risking {amount_to_risk}')
        return trade_size

    def check_stop_loss(self, current_price, entry_price, stop_loss_level, side):
        """
        Checks if a stop-loss level has been breached.
        :param current_price: The current market price.
        :param entry_price: The price at which the position was entered.
        :param stop_loss_level: The absolute price level for the stop-loss.
        :param side: 'buy' or 'sell' (indicating a long or short position).
        :return: True if stop-loss is breached, False otherwise.
        """
        if side.lower() == 'buy': # Long position, stop-loss is below entry
            if current_price <= stop_loss_level:
                logger.info(f'Stop-loss breached for LONG position: current_price {current_price} <= stop_loss_level {stop_loss_level}')
                return True
        elif side.lower() == 'sell': # Short position, stop-loss is above entry
            if current_price >= stop_loss_level:
                logger.info(f'Stop-loss breached for SHORT position: current_price {current_price} >= stop_loss_level {stop_loss_level}')
                return True
        else:
            logger.warning(f'Invalid side "{side}" for stop-loss check.')
            return False # Or raise error
        return False
