#!/usr/bin/env python3
"""
Simplified Check-in Verification Script

This script checks for users who need follow-ups without using complex Firestore queries
that require special indexes.
"""

import logging
from config.firebase_config import get_db
from datetime import datetime, timezone, timedelta
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Target user ID for checking
TARGET_USER_ID = "2348023672476"

def get_all_checkins_for_user(user_id, limit=20):
    """
    Get all check-ins for a user without complex filtering that requires indexes.
    We'll filter in Python to avoid Firestore index requirements.
    """
    db = get_db()
    
    # Simple query by user_id only, which doesn't require a composite index
    query = db.collection('checkins').where('user_id', '==', user_id).limit(limit)
    
    try:
        results = list(query.stream())
        logger.info(f"Found {len(results)} check-ins for user {user_id}")
        return results
    except Exception as e:
        logger.error(f"Error fetching check-ins: {str(e)}")
        return []

def get_user_data(user_id):
    """Get user data from Firestore"""
    db = get_db()
    user_doc = db.collection('users').document(user_id).get()
    
    if user_doc.exists:
        return user_doc.to_dict()
    else:
        logger.error(f"User {user_id} not found")
        return None

def check_reminder_eligibility(user_id):
    """Check if the user is eligible for reminders"""
    checkins = get_all_checkins_for_user(user_id)
    
    if not checkins:
        logger.info(f"No check-ins found for user {user_id}")
        return None
    
    # Separate system messages and user responses
    system_messages = []
    user_responses = []
    
    for doc in checkins:
        data = doc.to_dict()
        is_response = data.get('is_response', False)
        created_at = data.get('created_at')
        
        if created_at and is_response:
            user_responses.append({
                'id': doc.id,
                'content': data.get('response'),
                'time': created_at
            })
        elif created_at:
            system_messages.append({
                'id': doc.id,
                'content': data.get('response'),
                'time': created_at
            })
    
    # Sort by time (newest first)
    user_responses.sort(key=lambda x: x['time'], reverse=True)
    system_messages.sort(key=lambda x: x['time'], reverse=True)
    
    logger.info(f"Found {len(user_responses)} user responses and {len(system_messages)} system messages")
    
    # If no system messages, can't check for reminders
    if not system_messages:
        logger.info("No system messages found to check for reminder eligibility")
        return None
    
    # Get the latest system message
    latest_system = system_messages[0]
    
    # Check if user has already responded to the latest system message
    latest_response = user_responses[0] if user_responses else None
    
    if latest_response and latest_response['time'] > latest_system['time']:
        logger.info("User has already responded to the latest system message")
        return None
    
    # Calculate time since the latest system message
    now = datetime.now(timezone.utc)
    
    # Ensure timezone-aware comparison
    system_time = latest_system['time']
    if system_time.tzinfo is None:
        system_time = system_time.replace(tzinfo=timezone.utc)
    
    time_since_checkin = now - system_time
    
    # Check which reminder window the user falls into
    if timedelta(hours=1.5) < time_since_checkin <= timedelta(hours=2.5):
        return "morning"
    elif timedelta(hours=3.5) < time_since_checkin <= timedelta(hours=4.5):
        return "midday"
    elif timedelta(hours=7.5) < time_since_checkin <= timedelta(hours=8.5):
        return "evening"
    elif time_since_checkin > timedelta(hours=24):
        return "nextday"
    else:
        return None

def print_user_info(user_id):
    """Print user information and reminder eligibility"""
    user_data = get_user_data(user_id)
    if not user_data:
        return
    
    logger.info("="*50)
    logger.info(f"USER INFO: {user_id}")
    logger.info("="*50)
    logger.info(f"Name: {user_data.get('name', 'Unknown')}")
    logger.info(f"Account Index: {user_data.get('account_index', 0)}")
    logger.info(f"Account Status: {'Active' if user_data.get('is_active', True) else 'Inactive'}")
    
    reminder_type = check_reminder_eligibility(user_id)
    
    if reminder_type:
        logger.info(f"REMINDER NEEDED: {reminder_type.upper()}")
        logger.info("\nTo send this reminder, update the .env file with:")
        logger.info("WHATSAPP_API_URL=https://graph.facebook.com/v17.0")
        logger.info("WHATSAPP_PHONE_ID_0=<your-phone-id>")
        logger.info("WHATSAPP_ACCESS_TOKEN_0=<your-access-token>")
        logger.info("ENABLE_CRON=True")
        logger.info("CRON_SECRET=<your-secret>")
        logger.info("\nThen run: python trigger_reminder.py")
    else:
        logger.info("No reminder needed at this time")

if __name__ == "__main__":
    logger.info("Starting simplified check-in verification")
    print_user_info(TARGET_USER_ID) 