from flask import Blueprint, render_template
import logging

bp = Blueprint('main', __name__)
logger = logging.getLogger(__name__)

@bp.route('/')
def index():
    logger.info('Serving index page')
    return render_template('index.html')

@bp.route('/dashboard')
def dashboard():
    logger.info('Serving dashboard page')
    return render_template('dashboard.html')

@bp.route('/strategy-maker')
def strategy_maker():
    logger.info('Serving strategy maker page')
    return render_template('strategy_maker.html')

@bp.route('/chart-view')
def chart_view():
    logger.info('Serving chart view page')
    return render_template('chart_view.html')

@bp.route('/settings')
def settings_page():
    logger.info('Serving settings page')
    return render_template('settings.html')

@bp.route('/console')
def console_page():
    logger.info('Serving console page')
    return render_template('console.html')
