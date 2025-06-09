from app import db
# For JSON type, SQLAlchemy provides sqlalchemy.types.JSON.
# Flask-SQLAlchemy's db.JSON usually handles this well for supported backends (PostgreSQL, MySQL, modern SQLite).
# For older SQLite without JSON1 extension, it might store as TEXT and require manual JSON conversion,
# or one might use a TypeDecorator for automatic serialization/deserialization.
# We'll proceed with db.JSON assuming a reasonably modern setup.

class CustomStrategyModel(db.Model):
    __tablename__ = 'custom_strategies'
    id = db.Column(db.Integer, primary_key=True)
    # Assuming user_id 1 for single user context, or make nullable=False if users are properly implemented
    # Link to user_settings.id as UserSettings model has 'id' as primary_key, not 'user_id'
    user_id = db.Column(db.Integer, db.ForeignKey('user_settings.id'), nullable=False, default=1)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    configuration = db.Column(db.JSON, nullable=False)

    # Optional: Define relationship to UserSettings if needed for ORM features
    # user = db.relationship('UserSettings', backref=db.backref('custom_strategies', lazy='dynamic'))

    def __repr__(self):
        return f'<CustomStrategyModel {self.id}: {self.name}>'
