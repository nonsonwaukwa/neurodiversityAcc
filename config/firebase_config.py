import firebase_admin
from firebase_admin import credentials, firestore
import os
import json
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logger
logger = logging.getLogger(__name__)

# Reference to Firestore database
db = None

def initialize_firebase():
    """Initialize Firebase Admin SDK"""
    global db
    
    # Check if already initialized
    if firebase_admin._apps:
        db = firestore.client()
        return db
    
    try:
        # First try to get credentials from JSON in environment variables
        firebase_credentials_json = os.environ.get('FIREBASE_CREDENTIALS')
        if firebase_credentials_json:
            try:
                # Parse the JSON string from environment variable
                cred_dict = json.loads(firebase_credentials_json)
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred)
                logger.info("Firebase Admin initialized with credentials from environment variable")
            except Exception as json_err:
                logger.error(f"Error parsing Firebase credentials JSON: {json_err}")
                # Fall back to other methods
                firebase_credentials_json = None
        
        # If no JSON credentials, try file path
        if not firebase_credentials_json:
            # Get credentials file path from environment
            cred_path = os.environ.get('FIREBASE_CREDENTIALS_PATH', './config/firebase-credentials.json')
            if os.path.exists(cred_path):
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
                logger.info(f"Firebase Admin initialized with credentials from: {cred_path}")
            else:
                # Try default credentials (for Google Cloud environment)
                firebase_admin.initialize_app()
                logger.info("Firebase Admin initialized with default credentials")
    except Exception as e:
        logger.error(f"Failed to initialize Firebase: {e}")
        raise
    
    # Get a reference to the Firestore database
    db = firestore.client()
    
    return db

def get_db():
    """Get a reference to the Firestore database"""
    global db
    if db is None:
        db = initialize_firebase()
    return db 