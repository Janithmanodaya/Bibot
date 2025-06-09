from flask import Blueprint, jsonify, request
from app.services import db_service
from app.utils.encryption import ENCRYPTION_KEY
import logging

bp = Blueprint('api', __name__)
logger = logging.getLogger(__name__)

@bp.route('/status', methods=['GET'])
def get_status():
    logger.info('API /status called')
    return jsonify({'status': 'API is running'})

@bp.route('/settings', methods=['GET', 'POST'])
def manage_settings():
    if request.method == 'POST':
        data = request.json
        logger.info(f'API /settings POST called with data: {data}')
        # Placeholder: Save settings (e.g., API keys) using db_service
        # db_service.save_user_setting(user_id=1, api_key=data.get('apiKey'), api_secret=data.get('apiSecret'), exchange=data.get('exchange'), encryption_key=ENCRYPTION_KEY)
        return jsonify({'message': 'Settings saved (placeholder)', 'data': data}), 201
    else: # GET
        logger.info('API /settings GET called')
        # Placeholder: Load settings using db_service
        # setting = db_service.get_user_setting(user_id=1)
        # if setting:
        #     api_key_decrypted = setting.get_api_key(ENCRYPTION_KEY) if setting.encrypted_api_key else None
        #     return jsonify({'exchange': setting.selected_exchange, 'apiKey': api_key_decrypted})
        return jsonify({'message': 'Settings loaded (placeholder)', 'exchange': 'binance', 'apiKey': 'test_key'})

@bp.route('/start_strategy', methods=['POST'])
def start_strategy():
    data = request.json
    logger.info(f'API /start_strategy called with data: {data}')
    return jsonify({'message': 'Strategy started (placeholder)', 'strategy': data.get('strategyName')})

@bp.route('/stop_strategy', methods=['POST'])
def stop_strategy():
    logger.info('API /stop_strategy called')
    return jsonify({'message': 'Strategy stopped (placeholder)'})
