from app import create_app, db
# Import all models from app.models
from app.models.ohlc_data import OHLCData
from app.models.trade_history import TradeHistory
from app.models.user_settings import UserSettings

app = create_app()

with app.app_context():
    print("Creating database tables...")
    try:
        db.create_all()
        print("Database tables created successfully.")
    except Exception as e:
        print(f"Error creating database tables: {e}")
