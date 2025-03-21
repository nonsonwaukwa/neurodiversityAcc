#!/usr/bin/env python3
"""
Direct Reminder Tool

This script sends a direct reminder to the user by creating a new check-in entry in Firestore.
It bypasses WhatsApp API integration issues and works directly with Firestore.
"""

import logging
import sys
from config.firebase_config import get_db
from datetime import datetime, timezone
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Default target user ID
TARGET_USER_ID = "2348023672476"

def get_user_data(user_id):
    """Get user data from Firestore"""
    db = get_db()
    user_doc = db.collection('users').document(user_id).get()
    
    if user_doc.exists:
        return user_doc.to_dict()
    else:
        logger.error(f"User {user_id} not found")
        return None

def create_reminder_checkin(user_id, reminder_type=None):
    """Create a reminder check-in in Firestore directly"""
    db = get_db()
    user_data = get_user_data(user_id)
    
    if not user_data:
        logger.error(f"Cannot create reminder for unknown user: {user_id}")
        return False
    
    user_name = user_data.get('name', 'User')
    
    # Determine the message based on reminder type
    if reminder_type == 'morning' or reminder_type is None:
        message = (
            f"Hey {user_name}! 💫 Just a gentle check-in - absolutely no pressure at all. "
            f"I'm still here whenever you feel ready to connect. "
            f"How are you doing?"
        )
    elif reminder_type == 'midday':
        message = (
            f"Hi {user_name}! 🌤️ The day still holds possibilities, and that's wonderful. "
            f"If it feels right for you, how are you feeling right now?"
        )
    elif reminder_type == 'evening':
        message = (
            f"Hey {user_name}! ✨ How has your day unfolded? Remember, each day is its own journey, "
            f"and tomorrow offers a fresh beginning whenever you need it."
        )
    elif reminder_type == 'nextday':
        message = (
            f"Hi {user_name} 💖, I've noticed we haven't connected in a little while, and that's completely okay! "
            f"Sometimes we need space or things get busy, and I'm here with warmth whenever you're ready. "
            f"No rush at all. How are you doing?"
        )
    else:
        message = f"Hello {user_name}! How are you feeling today?"
    
    # Create a unique ID for the check-in
    checkin_id = str(uuid.uuid4())
    
    # Create check-in document data
    checkin_data = {
        'user_id': user_id,
        'response': message,
        'is_response': False,  # This is a system message, not a user response
        'created_at': datetime.now(timezone.utc),
        'needs_followup': True,
        'reminder_type': reminder_type or 'default',
        'sentiment_score': None
    }
    
    try:
        # Add the check-in to Firestore
        db.collection('checkins').document(checkin_id).set(checkin_data)
        
        logger.info(f"Successfully created reminder check-in for user {user_id}")
        logger.info(f"Check-in ID: {checkin_id}")
        logger.info(f"Message: {message}")
        
        return True
    except Exception as e:
        logger.error(f"Error creating reminder check-in: {str(e)}")
        return False

if __name__ == "__main__":
    # Default user ID and reminder type
    user_id = TARGET_USER_ID
    reminder_type = "morning"  # Default to morning reminder
    
    # Parse command line arguments if provided
    if len(sys.argv) > 1:
        user_id = sys.argv[1]
    if len(sys.argv) > 2:
        reminder_type = sys.argv[2]
    
    logger.info(f"Creating {reminder_type} reminder for user {user_id}...")
    
    # Create the reminder check-in
    success = create_reminder_checkin(user_id, reminder_type)
    
    if success:
        logger.info("="*50)
        logger.info(f"REMINDER CREATED SUCCESSFULLY")
        logger.info("="*50)
        logger.info("This reminder has been saved to the database.")
        logger.info("When WhatsApp API is properly configured, you would receive this message on WhatsApp.")
        logger.info("To make this work with WhatsApp, update the .env file with:")
        logger.info("WHATSAPP_API_URL=https://graph.facebook.com/v17.0")
        logger.info("WHATSAPP_PHONE_ID_0=<your-phone-id>")
        logger.info("WHATSAPP_ACCESS_TOKEN_0=<your-access-token>")
    else:
        logger.error("Failed to create reminder")
        sys.exit(1) 