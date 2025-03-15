import firebase_admin
from firebase_admin import credentials, firestore
import os
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Reference to Firestore database
db = None

def initialize_firebase():
    """Initialize Firebase Admin SDK"""
    global db
    
    # Check if already initialized
    if firebase_admin._apps:
        return
    
    # Get Firebase credentials
    firebase_credentials = os.environ.get('FIREBASE_CREDENTIALS')
    
    if firebase_credentials:
        # If credentials are provided as a JSON string in environment variable
        cred_dict = json.loads(firebase_credentials)
        cred = credentials.Certificate(cred_dict)
    else:
        # If credentials are in a file
        cred_path = os.environ.get('FIREBASE_CREDENTIALS_PATH', './config/firebase-credentials.json')
        if os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
        else:
            raise ValueError(
                "Firebase credentials not found. Please set either FIREBASE_CREDENTIALS environment variable " 
                "or provide a credentials file at FIREBASE_CREDENTIALS_PATH"
            )
    
    # Initialize the app
    firebase_admin.initialize_app(cred)
    
    # Get a reference to the Firestore database
    db = firestore.client()
    
    return db

def get_db():
    """Get a reference to the Firestore database"""
    global db
    if db is None:
        db = initialize_firebase()
    return db 