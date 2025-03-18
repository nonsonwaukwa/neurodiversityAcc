# Welcome to Cloud Functions for Firebase for Python!
# To get started, simply uncomment the below code or create your own.
# Deploy with `firebase deploy`

from firebase_functions import https_fn
import firebase_admin
from firebase_admin import initialize_app, firestore
import os
import logging
from flask import Flask

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Firebase Admin SDK if not already initialized
if not firebase_admin._apps:
    initialize_app()
    logger.info("Firebase Admin initialized")

# Import and initialize the Flask app
from app import create_app
app = create_app()

# Import routes after app initialization
from app.routes.admin import admin_bp
from app.routes.webhook import webhook_bp

# Register blueprints
app.register_blueprint(admin_bp)
app.register_blueprint(webhook_bp)

@https_fn.on_request()
def app_handler(req: https_fn.Request) -> https_fn.Response:
    """Handle all requests to the Firebase Function"""
    with app.request_context(req.environ):
        try:
            return app.full_dispatch_request()
        except Exception as e:
            logger.error(f"Error processing request: {e}")
            # Return a proper error response
            return https_fn.Response(
                f"Server Error: {str(e)}", 
                status=500, 
                headers={"Content-Type": "text/plain"}
            )

#
#
# @https_fn.on_request()
# def on_request_example(req: https_fn.Request) -> https_fn.Response:
#     return https_fn.Response("Hello world!")