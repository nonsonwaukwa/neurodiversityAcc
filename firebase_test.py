#!/usr/bin/env python3
"""
Firebase connection test script

This script tests if the Firebase configuration is working correctly.
It attempts to initialize Firebase and access Firestore.
"""

import os
from dotenv import load_dotenv
from config.firebase_config import initialize_firebase, get_db
import logging
from google.cloud import firestore
import firebase_admin
from firebase_admin import firestore

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_firebase_connection():
    """Test if Firebase connection works correctly"""
    print("Testing Firebase connection...")
    
    # Check if environment variables are set
    firebase_creds = os.environ.get('FIREBASE_CREDENTIALS')
    firebase_path = os.environ.get('FIREBASE_CREDENTIALS_PATH')
    
    if not firebase_creds and not firebase_path:
        print("WARNING: Neither FIREBASE_CREDENTIALS nor FIREBASE_CREDENTIALS_PATH environment variables are set!")
        print("Make sure at least one is configured in your .env file.")
        return False
    
    if firebase_creds:
        print("Found FIREBASE_CREDENTIALS environment variable")
    if firebase_path:
        print(f"Found FIREBASE_CREDENTIALS_PATH: {firebase_path}")
        if not os.path.exists(firebase_path):
            print(f"WARNING: The file {firebase_path} does not exist!")
            return False
    
    try:
        # Initialize Firebase
        print("Initializing Firebase...")
        initialize_firebase()
        
        # Get Firestore instance
        db = get_db()
        
        # Test a simple Firestore operation
        print("Testing Firestore access...")
        collections = list(db.collections())
        print(f"Available collections: {[collection.id for collection in collections]}")
        
        print("Firebase connection test successful!")
        return True
    
    except Exception as e:
        print(f"Firebase connection test failed: {str(e)}")
        return False

def test_firestore_connection():
    """Test Firestore database connection and basic operations"""
    try:
        # Initialize Firebase
        logger.info("Initializing Firebase...")
        initialize_firebase()
        
        # Get database reference
        db = get_db()
        logger.info("Successfully connected to Firestore")
        
        # Try a simple write operation
        test_ref = db.collection('test').document('connection_test')
        test_ref.set({
            'status': 'success',
            'timestamp': firestore.SERVER_TIMESTAMP
        })
        logger.info("Successfully wrote to Firestore")
        
        # Try a simple read operation
        doc = test_ref.get()
        if doc.exists:
            logger.info("Successfully read from Firestore")
            logger.info(f"Test document data: {doc.to_dict()}")
        
        # Clean up test document
        test_ref.delete()
        logger.info("Successfully deleted test document")
        
        return True
        
    except Exception as e:
        logger.error(f"Error testing Firestore connection: {e}")
        return False

if __name__ == "__main__":
    test_firebase_connection()
    test_firestore_connection() 