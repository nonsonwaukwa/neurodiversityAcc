#!/usr/bin/env python3
"""
Backdated Check-in Generator

This script creates a backdated check-in to make a user immediately eligible for 
morning, midday, or evening reminders without waiting for the natural time windows.
"""

import logging
from datetime import datetime, timezone, timedelta
import sys
from app import create_app
from app.models.checkin import CheckIn
from app.models.user import User
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Default values
DEFAULT_USER_ID = "2348023672476"
DEFAULT_REMINDER_TYPE = "morning"  # Options: morning, midday, evening

def create_backdated_checkin(user_id, reminder_type):
    """
    Create a backdated check-in to make the user immediately eligible for the specified reminder
    
    Args:
        user_id (str): User ID to create check-in for
        reminder_type (str): Type of reminder to be eligible for (morning, midday, evening)
    
    Returns:
        str: ID of the created check-in
    """
    # Get user info
    user = User.get(user_id)
    if not user:
        logger.error(f"User {user_id} not found")
        return None
    
    # Calculate the backdated time based on the reminder type
    now = datetime.now(timezone.utc)
    
    if reminder_type == "morning":
        # Morning reminder window: 1.5-2.5 hours after check-in
        # Create check-in from 2 hours ago to be in the middle of the window
        hours_ago = 2
    elif reminder_type == "midday":
        # Midday reminder window: 3.5-4.5 hours after check-in
        # Create check-in from 4 hours ago to be in the middle of the window
        hours_ago = 4
    elif reminder_type == "evening":
        # Evening reminder window: 7.5-8.5 hours after check-in
        # Create check-in from 8 hours ago to be in the middle of the window
        hours_ago = 8
    else:
        logger.error(f"Invalid reminder type: {reminder_type}")
        return None
    
    # Calculate backdated timestamp
    backdated_time = now - timedelta(hours=hours_ago)
    
    # Build check-in message
    if reminder_type == "morning":
        message = f"Good morning {user.name}! How are you feeling today?"
    elif reminder_type == "midday":
        message = f"Good afternoon {user.name}! How is your day going so far?"
    elif reminder_type == "evening":
        message = f"Good evening {user.name}! How has your day been?"
    
    # Generate unique ID
    checkin_id = str(uuid.uuid4())
    
    # Create check-in directly in the database
    from config.firebase_config import get_db
    db = get_db()
    
    # Create check-in data with backdated timestamp
    data = {
        'checkin_id': checkin_id,
        'user_id': user_id,
        'response': message,
        'is_response': False,  # This is a system message
        'created_at': backdated_time,
        'needs_followup': True,
        'reminder_type': 'system'
    }
    
    # Save to Firestore
    db.collection('checkins').document(checkin_id).set(data)
    
    logger.info(f"Created backdated check-in for {user.name}")
    logger.info(f"Check-in ID: {checkin_id}")
    logger.info(f"Message: {message}")
    logger.info(f"Timestamp: {backdated_time} ({hours_ago} hours ago)")
    logger.info(f"This makes the user eligible for {reminder_type} reminders")
    
    return checkin_id

def verify_eligibility(user_id, checkin_id):
    """Verify that the user is now eligible for reminders"""
    from app.cron.reminders import _send_reminder_if_needed
    
    # Create a fake WhatsApp service to test eligibility
    class FakeWhatsAppService:
        def __init__(self):
            self.messages = []
            
        def send_interactive_buttons(self, recipient, message, buttons):
            self.messages.append({
                'recipient': recipient,
                'message': message,
                'buttons': buttons,
                'type': 'interactive'
            })
            logger.info(f"[TESTING] Would send interactive message to {recipient}")
            return {'success': True}
            
        def send_message(self, recipient, message):
            self.messages.append({
                'recipient': recipient,
                'message': message,
                'type': 'text'
            })
            logger.info(f"[TESTING] Would send text message to {recipient}")
            return {'success': True}
    
    # Get user
    user = User.get(user_id)
    fake_service = FakeWhatsAppService()
    
    # Import the required functions
    from unittest.mock import patch
    
    # Create mock analytics and task services
    class MockAnalyticsService:
        @staticmethod
        def get_sentiment_trend(user_id, days=14):
            return {"trend": "neutral", "average": 0, "samples": 0}

    class MockTaskService:
        @staticmethod
        def get_self_care_tip():
            return "Take a few deep breaths."
    
    # Test eligibility with mocked services
    with patch('app.cron.reminders.get_analytics_service', return_value=MockAnalyticsService()), \
         patch('app.cron.reminders.get_task_service', return_value=MockTaskService()):
        
        logger.info("Testing morning reminder eligibility:")
        _send_reminder_if_needed(user, fake_service, "morning")
        
        logger.info("Testing midday reminder eligibility:")
        _send_reminder_if_needed(user, fake_service, "midday")
        
        logger.info("Testing evening reminder eligibility:")
        _send_reminder_if_needed(user, fake_service, "evening")
    
    # Check results
    if fake_service.messages:
        logger.info(f"SUCCESS! User is now eligible for reminders.")
        logger.info(f"Would have sent {len(fake_service.messages)} messages")
        return True
    else:
        logger.error("User is still not eligible for any reminders")
        return False

def verify_with_real_cron(reminder_type):
    """Verify by calling the actual cron endpoint"""
    import requests
    import os
    
    # Get the cron secret and base URL
    cron_secret = os.environ.get("CRON_SECRET")
    base_url = os.environ.get("BASE_URL", "https://neurodiversityacc.up.railway.app")
    
    if not cron_secret:
        logger.error("CRON_SECRET environment variable not set. Can't verify with real cron.")
        return False
    
    # Call the cron endpoint directly
    url = f"{base_url}/api/cron/followup-reminders"
    headers = {"X-Cron-Secret": cron_secret}
    data = {"reminder_type": reminder_type}
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        response.raise_for_status()
        
        logger.info(f"Cron endpoint response: {response.status_code} {response.text}")
        return True
    except Exception as e:
        logger.error(f"Error calling cron endpoint: {e}")
        return False

if __name__ == "__main__":
    # Parse command line arguments
    user_id = DEFAULT_USER_ID
    reminder_type = DEFAULT_REMINDER_TYPE
    trigger_cron = False
    
    # Parse arguments
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg == "--trigger-cron":
            trigger_cron = True
        elif arg in ["morning", "midday", "evening"]:
            reminder_type = arg
        elif i == 1 and arg not in ["--trigger-cron"]:
            reminder_type = arg
        elif i == 2 and arg not in ["--trigger-cron"]:
            user_id = arg
    
    # Validate reminder type
    valid_types = ["morning", "midday", "evening"]
    if reminder_type not in valid_types:
        logger.error(f"Invalid reminder type: {reminder_type}")
        logger.error(f"Must be one of: {', '.join(valid_types)}")
        sys.exit(1)
    
    # Create Flask app and set up application context
    logger.info(f"Creating backdated check-in for {reminder_type} reminder eligibility")
    logger.info(f"User ID: {user_id}")
    
    app = create_app()
    with app.app_context():
        # Create backdated check-in
        checkin_id = create_backdated_checkin(user_id, reminder_type)
        
        if not checkin_id:
            logger.error("Failed to create backdated check-in")
            sys.exit(1)
        
        # Verify eligibility
        logger.info("Verifying reminder eligibility...")
        is_eligible = verify_eligibility(user_id, checkin_id)
        
        if is_eligible:
            logger.info("="*80)
            logger.info(f"SUCCESS: User is now eligible for {reminder_type} reminders")
            logger.info("="*80)
            logger.info("To trigger the actual reminder, run the cron job:")
            logger.info(f"curl -X POST https://neurodiversityacc.up.railway.app/api/cron/followup-reminders \\\n"
                      f"     -H 'X-Cron-Secret: YOUR_SECRET' \\\n"
                      f"     -H 'Content-Type: application/json' \\\n"
                      f"     -d '{{\"reminder_type\": \"{reminder_type}\"}}'")
            
            # Verify with real cron if requested
            if trigger_cron:
                logger.info("="*80)
                logger.info("Triggering reminder via cron endpoint...")
                verify_with_real_cron(reminder_type)
        else:
            logger.error("="*80)
            logger.error(f"FAILED: User is still not eligible for {reminder_type} reminders")
            logger.error("="*80) 