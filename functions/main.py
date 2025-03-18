import firebase_admin
from firebase_admin import credentials
from functions_framework import http
from flask import Flask, request
from app import create_app
import os
import json

# Initialize Firebase Admin if not already initialized
if not firebase_admin._apps:
    try:
        # Try to get credentials from environment variable
        cred_json = os.environ.get('FIREBASE_CONFIG')
        if cred_json:
            config = json.loads(cred_json)
            cred_json = config.get('app', {}).get('credentials')
            if cred_json:
                cred_dict = json.loads(cred_json)
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred)
            else:
                print("No credentials found in FIREBASE_CONFIG")
        else:
            # Fallback to local file for development
            cred_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'firebase-credentials.json')
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
    except Exception as e:
        print(f"Error initializing Firebase: {e}")
        # In production, Firebase will automatically initialize

# Create Flask app
app = create_app()

@http
def app_function(request):
    """Handle all requests to the Firebase Function."""
    return app(request.environ, lambda x, y: y)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port) 