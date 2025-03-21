#!/usr/bin/env python3
"""
Cron Job Trigger

This script triggers the reminder cron job directly to send follow-up reminders
to eligible users.
"""

import logging
import sys
import requests
import os
import json
from app import create_app
from app.models.user import User

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def trigger_cron_job(reminder_type="morning"):
    """
    Trigger the follow-up reminders cron job
    
    Args:
        reminder_type (str): Type of reminder to send
    """
    # Get the cron secret from environment variables
    cron_secret = os.environ.get("CRON_SECRET")
    
    if not cron_secret:
        from flask import current_app
        cron_secret = current_app.config.get("CRON_SECRET")
        
    if not cron_secret:
        logger.error("CRON_SECRET not found in environment or app config")
        return False
    
    # Build request
    base_url = os.environ.get("BASE_URL", "https://neurodiversityacc.up.railway.app")
    url = f"{base_url}/api/cron/followup-reminders"
    headers = {
        "X-Cron-Secret": cron_secret,
        "Content-Type": "application/json"
    }
    payload = {"reminder_type": reminder_type}
    
    logger.info(f"Triggering {reminder_type} follow-up reminders")
    logger.info(f"URL: {url}")
    
    try:
        # Make request
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        
        logger.info(f"Status code: {response.status_code}")
        if response.status_code == 200:
            logger.info(f"Response: {json.dumps(response.json(), indent=2)}")
            logger.info(f"Successfully triggered {reminder_type} reminders!")
            return True
        else:
            logger.error(f"Failed to trigger reminders: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Error triggering reminders: {str(e)}")
        return False

def list_eligible_users(reminder_type="morning"):
    """
    List users who are eligible for reminders
    """
    from app.cron.reminders import _send_reminder_if_needed
    
    # Get all users
    users = User.get_all_active()
    logger.info(f"Found {len(users)} active users")
    
    # Create a fake WhatsApp service to test eligibility
    class FakeWhatsAppService:
        def __init__(self):
            self.messages = []
            self.eligible_users = []
            
        def send_interactive_buttons(self, recipient, message, buttons):
            self.messages.append({
                'recipient': recipient,
                'message': message,
                'buttons': buttons,
                'type': 'interactive'
            })
            self.eligible_users.append(recipient)
            return {'success': True}
            
        def send_message(self, recipient, message):
            self.messages.append({
                'recipient': recipient,
                'message': message,
                'type': 'text'
            })
            self.eligible_users.append(recipient)
            return {'success': True}
    
    # Check each user for eligibility
    fake_service = FakeWhatsAppService()
    eligible_users = []
    
    for user in users:
        # Import for mocking
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
            
            # Check if the user is eligible for this reminder type
            _send_reminder_if_needed(user, fake_service, reminder_type)
    
    # Show eligible users
    if fake_service.eligible_users:
        logger.info(f"Found {len(set(fake_service.eligible_users))} users eligible for {reminder_type} reminders:")
        for user_id in set(fake_service.eligible_users):
            user = User.get(user_id)
            logger.info(f"  - {user.name} (ID: {user_id})")
        return True
    else:
        logger.info(f"No users eligible for {reminder_type} reminders")
        return False

if __name__ == "__main__":
    # Parse command line arguments
    reminder_type = "morning"
    check_only = False
    
    for arg in sys.argv[1:]:
        if arg in ["morning", "midday", "evening", "nextday"]:
            reminder_type = arg
        elif arg == "--check":
            check_only = True
    
    # Create Flask app and app context
    app = create_app()
    with app.app_context():
        logger.info(f"Checking for users eligible for {reminder_type} reminders")
        
        # List eligible users
        has_eligible_users = list_eligible_users(reminder_type)
        
        if has_eligible_users and not check_only:
            logger.info(f"Triggering {reminder_type} reminders")
            trigger_cron_job(reminder_type)
        elif not has_eligible_users:
            logger.info("No eligible users found. No reminders will be sent.")
            logger.info("Run 'create_backdated_checkin.py morning' to create a backdated check-in")
        elif check_only:
            logger.info("Check-only mode - not triggering reminders")
            logger.info("Run without --check to trigger reminders") 