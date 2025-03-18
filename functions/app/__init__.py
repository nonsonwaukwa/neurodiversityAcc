from flask import Flask
from flask_cors import CORS
import os
import json
from dotenv import load_dotenv
import logging
import sys
from datetime import datetime

# Load environment variables
load_dotenv()

# Configure logging once at the root level
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)

# Prevent duplicate logs by removing default handlers
logging.getLogger('werkzeug').handlers = []
logger = logging.getLogger(__name__)

def create_app(config_class=None):
    """Create and configure the Flask application"""
    app = Flask(__name__)
    
    # Enable CORS
    CORS(app)
    
    # Load configuration
    if config_class:
        app.config.from_object(config_class)
    else:
        # Load the default Config class from settings
        from config.settings import Config
        app.config.from_object(Config)
        logger.info("Loaded configuration from config.settings.Config")
    
    # Import and register blueprints
    from app.routes.webhook import webhook_bp
    from app.routes.admin import admin_bp
    
    app.register_blueprint(webhook_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    
    # Try to register other blueprints if they exist
    try:
        from app.routes.cron import cron_bp
        app.register_blueprint(cron_bp, url_prefix='/api')
    except ImportError:
        logger.warning("Cron blueprint not found")
        
    try:
        from app.routes.health import health_bp
        app.register_blueprint(health_bp)
    except ImportError:
        logger.warning("Health blueprint not found")
    
    @app.route('/')
    def home():
        return {'status': 'ok', 'message': 'Neurodiversity Accountability System API is running'}
    
    # Add template filters
    @app.template_filter('datetime')
    def format_datetime(value):
        """Format a datetime object to a readable string"""
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                return value
        return value.strftime('%Y-%m-%d %H:%M:%S') if value else ''
    
    # Add Chart.js to template context
    @app.context_processor
    def inject_chart_js():
        return {
            'chart_js_url': 'https://cdn.jsdelivr.net/npm/chart.js'
        }
    
    return app 