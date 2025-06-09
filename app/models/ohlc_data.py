from app import db

class OHLCData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    exchange = db.Column(db.String(50), nullable=False)
    symbol = db.Column(db.String(20), nullable=False)
    timeframe = db.Column(db.String(10), nullable=False)  # e.g., 1m, 5m, 1h, 1d
    open_time = db.Column(db.BigInteger, nullable=False) # Timestamp from exchange
    open_price = db.Column(db.Float)
    high_price = db.Column(db.Float)
    low_price = db.Column(db.Float)
    close_price = db.Column(db.Float)
    volume = db.Column(db.Float)
    close_time = db.Column(db.BigInteger)

    __table_args__ = (db.UniqueConstraint('exchange', 'symbol', 'timeframe', 'open_time', name='_exchange_symbol_timeframe_opentime_uc'),)

    def __repr__(self):
        return f'<OHLCData {self.symbol} {self.timeframe} {self.open_time}>'
