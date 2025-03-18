from flask import Flask
from flask_cors import CORS
import os
from dotenv import load_dotenv
import logging
import sys
from firebase_admin import credentials, initialize_app

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
        # Import config only when needed to avoid circular imports
        from config.settings import Config
        app.config.from_object(Config)
    
    # Initialize Firebase
    from config.firebase_config import initialize_firebase
    initialize_firebase()
    logger.info("Firebase initialized - using Firebase for database operations")
    
    # Initialize Firebase Admin
    cred = credentials.Certificate('path/to/serviceAccountKey.json')
    initialize_app(cred)
    
    # Import and register blueprints
    from app.routes.webhook import webhook_bp
    from app.routes.admin import admin_bp
    from app.routes.cron import cron_bp
    from app.routes.health import health_bp
    
    app.register_blueprint(webhook_bp)
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(cron_bp, url_prefix='/api')
    app.register_blueprint(health_bp)
    
    @app.route('/')
    def home():
        return {'status': 'ok', 'message': 'Neurodiversity Accountability System API is running'}
    
    # Add Chart.js to template context
    @app.context_processor
    def inject_chart_js():
        return {
            'chart_js_url': 'https://cdn.jsdelivr.net/npm/chart.js'
        }
    
    return app 