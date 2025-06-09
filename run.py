from app import create_app, socketio # Import socketio
from app.models import UserSetting, TradeHistory, OHLCData # For initdb
from app import db # For initdb

app = create_app()

def init_db():
    with app.app_context():
        print('Initialized the database and created tables.')

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'initdb':
        init_db()
    else:
        print('Starting Flask-SocketIO server...')
        socketio.run(app, debug=True, host='0.0.0.0', port=5000)
