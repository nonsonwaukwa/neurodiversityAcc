from flask import Flask
from flask_cors import CORS
import os
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
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
    
    # Import and register blueprints
    from app.routes.webhook import webhook_bp
    from app.routes.admin import admin_bp
    from app.routes.cron import cron_bp
    from app.routes.health import health_bp
    
    app.register_blueprint(webhook_bp, url_prefix='/api')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(cron_bp, url_prefix='/api')
    app.register_blueprint(health_bp)
    
    @app.route('/')
    def home():
        return {'status': 'ok', 'message': 'Neurodiversity Accountability System API is running'}
    
    return app 