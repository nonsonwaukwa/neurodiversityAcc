from flask import Flask
from flask_cors import CORS
import os
import json
from dotenv import load_dotenv
import logging
import sys
from firebase_admin import credentials, initialize_app
import firebase_admin

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

# Initialize Firebase Admin SDK
try:
    # Check if already initialized
    if not firebase_admin._apps:
        # First try to get credentials from JSON in environment variables
        firebase_credentials_json = os.environ.get('FIREBASE_CREDENTIALS')
        if firebase_credentials_json:
            try:
                # Parse the JSON string from environment variable
                cred_dict = json.loads(firebase_credentials_json)
                cred = credentials.Certificate(cred_dict)
                initialize_app(cred)
                logger.info("Firebase Admin initialized with credentials from environment variable")
            except Exception as json_err:
                logger.error(f"Error parsing Firebase credentials JSON: {json_err}")
                # Fall back to other methods
                firebase_credentials_json = None
        
        # If no JSON credentials, try other methods
        if not firebase_credentials_json:
            # If running in Firebase Functions, use default credentials
            if os.environ.get('FUNCTION_TARGET'):
                initialize_app()
                logger.info("Firebase Admin initialized with default credentials")
            else:
                # For local development, use credentials file from env var
                creds_path = os.environ.get('FIREBASE_CREDENTIALS_PATH')
                if creds_path and os.path.exists(creds_path):
                    cred = credentials.Certificate(creds_path)
                    initialize_app(cred)
                    logger.info(f"Firebase Admin initialized with credentials from: {creds_path}")
                else:
                    logger.warning("Firebase credentials not found, trying default credentials")
                    initialize_app()
    else:
        logger.info("Firebase Admin already initialized")
except Exception as e:
    logger.error(f"Error initializing Firebase Admin: {e}")

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
    
    # Add Chart.js to template context
    @app.context_processor
    def inject_chart_js():
        return {
            'chart_js_url': 'https://cdn.jsdelivr.net/npm/chart.js'
        }
    
    return app 