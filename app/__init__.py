from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
import os
import logging
from logging.handlers import RotatingFileHandler
from app.utils.log_handler import SocketIOHandler # Import custom handler

db = SQLAlchemy()
# Initialize SocketIO with logger=True for its own internal logs, engineio_logger for Engine.IO logs
# These logs will go to the standard logging setup.
socketio = SocketIO(logger=False, engineio_logger=False)

def setup_logging(app):
    # Remove default Flask handler if it exists
    if app.logger.hasHandlers():
        app.logger.handlers.clear()

    # Common formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s [in %(pathname)s:%(lineno)d]')

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.DEBUG if app.debug else logging.INFO)

    # File Handler
    if not os.path.exists('logs'):
        os.mkdir('logs')
    file_handler = RotatingFileHandler('logs/app.log', maxBytes=100*1024*1024, backupCount=5) # 100MB per file
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    # SocketIO Handler for sending logs to frontend
    # This handler will be added to the root logger.
    # Its set_emitter method will be called later by register_socketio_handlers
    # once the sio_instance is fully available and routes are being set up.
    socketio_log_handler = SocketIOHandler()
    socketio_log_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')) # Simpler format for frontend
    socketio_log_handler.setLevel(logging.INFO) # Send INFO and above to frontend console

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.handlers.clear() # Clear any pre-existing handlers
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    if not app.config.get('TESTING', False): # Do not add socketio handler during tests or if explicitly disabled
        root_logger.addHandler(socketio_log_handler)

    root_logger.setLevel(logging.DEBUG if app.debug else logging.INFO)

    # Configure specific loggers (Flask app, SQLAlchemy, etc.)
    # Stop them from propagating to the root if they have specific handlers,
    # or let them propagate if they should use root handlers.
    # For now, let them propagate to use the root handlers.
    logging.getLogger('flask_app').setLevel(logging.DEBUG if app.debug else logging.INFO)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO) # Can be WARNING in prod
    logging.getLogger('socketio').setLevel(logging.INFO) # For SocketIO's own logs
    logging.getLogger('engineio').setLevel(logging.INFO) # For Engine.IO's own logs

    app.logger.info('Logging configured: Console, File, and SocketIOHandler prepared.')


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object('app.config.Config')
    # Optional: instance config, loaded if config.py exists in instance folder
    app.config.from_pyfile('config.py', silent=True)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.instance_path, 'trading_app.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass # Already exists or race condition, not critical

    # Initialize logging
    setup_logging(app)

    # Initialize extensions
    db.init_app(app)
    socketio.init_app(app) # Initialize SocketIO with the app

    # Import and register SocketIO event handlers
    # This must be done after socketio.init_app(app)
    from app.routes import socketio_events
    socketio_events.register_socketio_handlers(socketio) # Pass the initialized socketio instance

    with app.app_context():
        # Import models to ensure they are known to SQLAlchemy
        from . import models

        # Import and register blueprints
        from .routes import main_routes, api_routes # socketio_events is already imported and configured
        app.register_blueprint(main_routes.bp)
        app.register_blueprint(api_routes.bp, url_prefix='/api')

        app.logger.info('Application setup complete. Blueprints registered.')

    return app
