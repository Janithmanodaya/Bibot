from app import db
from sqlalchemy.sql import func

class TradeHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(100), unique=True, nullable=False)
    exchange = db.Column(db.String(50), nullable=False)
    symbol = db.Column(db.String(20), nullable=False)
    timestamp = db.Column(db.DateTime(timezone=True), server_default=func.now())
    type = db.Column(db.String(20))  # e.g., limit, market
    side = db.Column(db.String(10))  # e.g., buy, sell
    price = db.Column(db.Float)
    quantity = db.Column(db.Float)
    status = db.Column(db.String(20)) # e.g., filled, partial, cancelled

    def __repr__(self):
        return f'<TradeHistory {self.order_id} {self.symbol}>'
