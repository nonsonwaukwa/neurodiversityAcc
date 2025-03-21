#!/usr/bin/env python3
"""
Firestore Index Setup Guide

This script helps you set up the required Firestore indexes for proper operation
of the check-in and reminder system in the Neurodiversity Accountability App.
"""

import logging
import webbrowser
import sys
import os
from config.firebase_config import get_db
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_project_id():
    """Get the Firebase project ID from credentials or environment"""
    try:
        from google.oauth2 import service_account
        import json
        
        # Try to get project ID from credentials file
        creds_path = os.environ.get('FIREBASE_CREDENTIALS', './config/firebase-credentials.json')
        
        if os.path.exists(creds_path):
            with open(creds_path, 'r') as f:
                creds_data = json.load(f)
                project_id = creds_data.get('project_id')
                if project_id:
                    return project_id
        
        # If that didn't work, try to get it from Firestore client
        db = get_db()
        if hasattr(db, '_client') and hasattr(db._client, '_project'):
            return db._client._project
            
        # Last resort: prompt the user
        return input("Enter your Firebase project ID: ")
    except Exception as e:
        logger.error(f"Error getting project ID: {str(e)}")
        return input("Enter your Firebase project ID: ")

def generate_index_urls(project_id):
    """Generate URLs for creating each required index"""
    base_url = f"https://console.firebase.google.com/project/{project_id}/firestore/indexes"
    
    # Define the required indexes
    indexes = [
        {
            "name": "User check-ins with response filter",
            "collection": "checkins",
            "fields": [
                {"fieldPath": "user_id", "order": "ASCENDING"},
                {"fieldPath": "is_response", "order": "ASCENDING"},
                {"fieldPath": "created_at", "order": "DESCENDING"}
            ],
            "url": f"https://console.firebase.google.com/v1/r/project/{project_id}/firestore/indexes?create_composite=ClJwcm9qZWN0cy9uZXVyb2RpdmVyc2l0eWFjYy9kYXRhYmFzZXMvKGRlZmF1bHQpL2NvbGxlY3Rpb25Hcm91cHMvY2hlY2tpbnMvaW5kZXhlcy9fEAEaDwoLaXNfcmVzcG9uc2UQARoLCgd1c2VyX2lkEAEaDgoKY3JlYXRlZF9hdBACGgwKCF9fbmFtZV9fEAI"
        },
        {
            "name": "User check-ins by time",
            "collection": "checkins",
            "fields": [
                {"fieldPath": "user_id", "order": "ASCENDING"},
                {"fieldPath": "created_at", "order": "DESCENDING"}
            ],
            "url": f"https://console.firebase.google.com/v1/r/project/{project_id}/firestore/indexes?create_composite=ClFwcm9qZWN0cy9uZXVyb2RpdmVyc2l0eWFjYy9kYXRhYmFzZXMvKGRlZmF1bHQpL2NvbGxlY3Rpb25Hcm91cHMvY2hlY2tpbnMvaW5kZXhlcy9fEAEaCwoHdXNlcl9pZBABGg4KCmNyZWF0ZWRfYXQQAhoMCghfX25hbWVfXxAC"
        },
        {
            "name": "All responses by user",
            "collection": "checkins", 
            "fields": [
                {"fieldPath": "is_response", "order": "ASCENDING"},
                {"fieldPath": "user_id", "order": "ASCENDING"},
                {"fieldPath": "created_at", "order": "DESCENDING"}
            ],
            "url": f"https://console.firebase.google.com/v1/r/project/{project_id}/firestore/indexes?create_composite=ClJwcm9qZWN0cy9uZXVyb2RpdmVyc2l0eWFjYy9kYXRhYmFzZXMvKGRlZmF1bHQpL2NvbGxlY3Rpb25Hcm91cHMvY2hlY2tpbnMvaW5kZXhlcy9fEAEaDwoLaXNfcmVzcG9uc2UQARoLCgd1c2VyX2lkEAEaDgoKY3JlYXRlZF9hdBACGgwKCF9fbmFtZV9fEAI"
        }
    ]
    
    return indexes

def test_indexes(user_id="2348023672476"):
    """Test if indexes are working by running sample queries"""
    db = get_db()
    
    logger.info("Testing Firestore indexes...")
    
    test_results = []
    
    # Test index 1: User check-ins with response filter
    try:
        logger.info("Testing 'User check-ins with response filter' index...")
        query = db.collection('checkins')\
            .where('user_id', '==', user_id)\
            .where('is_response', '==', False)\
            .order_by('created_at', direction="DESCENDING")\
            .limit(5)
            
        results = list(query.stream())
        test_results.append({
            "name": "User check-ins with response filter",
            "success": True,
            "results": len(results)
        })
        logger.info(f"✅ Success! Found {len(results)} check-ins")
    except Exception as e:
        test_results.append({
            "name": "User check-ins with response filter",
            "success": False,
            "error": str(e)
        })
        logger.error(f"❌ Failed: {str(e)}")
    
    # Test index 2: User check-ins by time
    try:
        logger.info("Testing 'User check-ins by time' index...")
        query = db.collection('checkins')\
            .where('user_id', '==', user_id)\
            .order_by('created_at', direction="DESCENDING")\
            .limit(5)
            
        results = list(query.stream())
        test_results.append({
            "name": "User check-ins by time",
            "success": True,
            "results": len(results)
        })
        logger.info(f"✅ Success! Found {len(results)} check-ins")
    except Exception as e:
        test_results.append({
            "name": "User check-ins by time",
            "success": False,
            "error": str(e)
        })
        logger.error(f"❌ Failed: {str(e)}")
    
    # Test index 3: All responses by user
    try:
        logger.info("Testing 'All responses by user' index...")
        query = db.collection('checkins')\
            .where('is_response', '==', True)\
            .where('user_id', '==', user_id)\
            .order_by('created_at', direction="DESCENDING")\
            .limit(5)
            
        results = list(query.stream())
        test_results.append({
            "name": "All responses by user",
            "success": True,
            "results": len(results)
        })
        logger.info(f"✅ Success! Found {len(results)} responses")
    except Exception as e:
        test_results.append({
            "name": "All responses by user",
            "success": False,
            "error": str(e)
        })
        logger.error(f"❌ Failed: {str(e)}")
    
    return test_results

def print_summary(test_results, indexes):
    """Print a summary of the test results"""
    logger.info("\n" + "="*60)
    logger.info("FIRESTORE INDEX SETUP SUMMARY")
    logger.info("="*60)
    
    all_success = all(result["success"] for result in test_results)
    
    if all_success:
        logger.info("🎉 All indexes are working correctly! 🎉")
        logger.info("\nReminder system should now be able to query the database properly.")
        logger.info("Next steps:")
        logger.info("1. Configure WhatsApp API credentials in .env file")
        logger.info("2. Ensure ENABLE_CRON=True in .env file")
        logger.info("3. Restart the application")
    else:
        logger.info("⚠️ Some indexes are not working correctly and need to be created.")
        logger.info("\nPlease create the missing indexes using the following URLs:")
        
        for i, result in enumerate(test_results):
            if not result["success"]:
                logger.info(f"\n{i+1}. {result['name']}:")
                logger.info(f"   Error: {result.get('error', 'Unknown error')}")
                logger.info(f"   Create this index: {indexes[i]['url']}")
    
    logger.info("\nSee REMINDER_SYSTEM_GUIDE.md for more details on setting up the reminder system.")

def interactive_setup():
    """Interactive setup process for Firestore indexes"""
    logger.info("="*60)
    logger.info("FIRESTORE INDEX SETUP FOR NEURODIVERSITY ACCOUNTABILITY APP")
    logger.info("="*60)
    logger.info("\nThis script will help you set up the required Firestore indexes")
    logger.info("for proper operation of the check-in and reminder system.")
    
    # Get project ID
    project_id = get_project_id()
    logger.info(f"\nFirebase Project ID: {project_id}")
    
    # Generate index URLs
    indexes = generate_index_urls(project_id)
    
    # Test if indexes already exist
    test_results = test_indexes()
    failed_indexes = [i for i, result in enumerate(test_results) if not result["success"]]
    
    if not failed_indexes:
        logger.info("\n✅ All indexes are already set up correctly!")
        print_summary(test_results, indexes)
        return
    
    # Ask user if they want to set up the missing indexes
    logger.info(f"\n⚠️ Found {len(failed_indexes)} missing or invalid indexes.")
    choice = input("\nWould you like to set up the missing indexes now? (y/n): ")
    
    if choice.lower() != 'y':
        logger.info("\nSetup canceled. You can run this script again later.")
        return
    
    # Open browser tabs for each missing index
    logger.info("\nOpening browser tabs for each missing index...")
    for i in failed_indexes:
        index = indexes[i]
        logger.info(f"Opening browser for: {index['name']}")
        webbrowser.open(index['url'])
        time.sleep(1)  # Small delay to prevent browser from blocking multiple tabs
    
    logger.info("\nPlease follow these steps in each browser tab:")
    logger.info("1. Sign in to your Firebase account if prompted")
    logger.info("2. Review the index details")
    logger.info("3. Click 'Create index' button")
    logger.info("4. Wait for the index to be created (this may take a few minutes)")
    
    input("\nPress Enter when you've created all the indexes to test them again...")
    
    # Test indexes again
    logger.info("\nTesting indexes again...")
    test_results = test_indexes()
    print_summary(test_results, indexes)

if __name__ == "__main__":
    interactive_setup() 