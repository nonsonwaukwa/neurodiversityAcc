import firebase_admin
from firebase_admin import credentials
from firebase_functions import https_fn
from flask import Flask, request
from app import create_app

# Initialize Firebase Admin
cred = credentials.ApplicationDefault()
firebase_admin.initialize_app(cred)

# Create Flask app
app = create_app()

@https_fn.on_request()
def app_function(req: https_fn.Request) -> https_fn.Response:
    """Handle all requests to the Firebase Function."""
    with app.request_context(req.environ):
        return app.full_dispatch_request() 