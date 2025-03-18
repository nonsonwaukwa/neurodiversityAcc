# Welcome to Cloud Functions for Firebase for Python!
# To get started, simply uncomment the below code or create your own.
# Deploy with `firebase deploy`

from firebase_functions import https_fn
from firebase_admin import initialize_app
from flask import Flask, request
from firebase_admin import firestore
import os

# Initialize Firebase Admin
initialize_app()

# Initialize Flask
app = Flask(__name__)

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
        return app.full_dispatch_request()

#
#
# @https_fn.on_request()
# def on_request_example(req: https_fn.Request) -> https_fn.Response:
#     return https_fn.Response("Hello world!")