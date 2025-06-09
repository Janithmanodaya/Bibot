from app import db
from app.utils.encryption import encrypt_data, decrypt_data # Assuming encryption utils will be there

class UserSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, unique=True, nullable=False) # Example: if multi-user
    selected_exchange = db.Column(db.String(50), default='binance')
    encrypted_api_key = db.Column(db.String(256))
    encrypted_api_secret = db.Column(db.String(256))
    use_testnet = db.Column(db.Boolean, default=False, nullable=False)
    max_account_drawdown_percentage = db.Column(db.Float, nullable=True, default=20.0)
    max_trade_size_percentage_balance = db.Column(db.Float, nullable=True, default=5.0)
    default_stop_loss_percentage = db.Column(db.Float, nullable=True, default=2.0)
    peak_account_equity = db.Column(db.Float, nullable=True, default=0.0) # Stores the highest equity achieved

    def set_api_credentials(self, api_key, api_secret, encryption_key):
        self.encrypted_api_key = encrypt_data(api_key.encode(), encryption_key)
        self.encrypted_api_secret = encrypt_data(api_secret.encode(), encryption_key)

    def get_api_key(self, encryption_key):
        if self.encrypted_api_key:
            return decrypt_data(self.encrypted_api_key, encryption_key).decode()
        return None

    def get_api_secret(self, encryption_key):
        if self.encrypted_api_secret:
            return decrypt_data(self.encrypted_api_secret, encryption_key).decode()
        return None

    def __repr__(self):
        return f'<UserSettings {self.user_id}>'
