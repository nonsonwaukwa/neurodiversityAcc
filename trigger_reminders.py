#!/usr/bin/env python3
"""
Direct Reminder Trigger

This script directly triggers the reminder function without relying on the cron endpoint.
It should be run within the app context to ensure all dependencies are available.
"""

import logging
import sys
import os
from app import create_app
from app.models.user import User
from app.cron.reminders import send_checkin_reminders
from unittest.mock import patch, MagicMock

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def trigger_direct_reminders(reminder_type="morning"):
    """
    Directly trigger the follow-up reminders function with a mock WhatsApp service
    
    Args:
        reminder_type (str): Type of reminder to send
    """
    logger.info(f"Directly triggering {reminder_type} follow-up reminders using mock WhatsApp service")
    
    try:
        # Create a mock WhatsApp service
        mock_whatsapp = MagicMock()
        mock_whatsapp.send_interactive_buttons.return_value = {"success": True}
        mock_whatsapp.send_message.return_value = {"success": True}
        
        # Track sent messages
        sent_messages = []
        
        def track_interactive_buttons(recipient, message, buttons):
            sent_messages.append({
                "type": "interactive",
                "recipient": recipient,
                "message": message,
                "buttons": buttons
            })
            logger.info(f"Would send interactive message to {recipient}: {message}")
            logger.info(f"With buttons: {buttons}")
            return {"success": True}
        
        def track_message(recipient, message):
            sent_messages.append({
                "type": "text",
                "recipient": recipient,
                "message": message
            })
            logger.info(f"Would send text message to {recipient}: {message}")
            return {"success": True}
        
        mock_whatsapp.send_interactive_buttons.side_effect = track_interactive_buttons
        mock_whatsapp.send_message.side_effect = track_message
        
        # Mock the WhatsApp service to use our mock
        with patch('app.services.whatsapp.get_whatsapp_service', return_value=mock_whatsapp):
            # Call the reminders function directly
            logger.info(f"Calling send_checkin_reminders with reminder_type={reminder_type}")
            result = send_checkin_reminders(reminder_type=reminder_type)
            
            if result:
                logger.info(f"Successfully processed {reminder_type} reminders")
                if sent_messages:
                    logger.info(f"Would have sent {len(sent_messages)} messages:")
                    for idx, msg in enumerate(sent_messages, 1):
                        logger.info(f"Message {idx}:")
                        logger.info(f"  - Recipient: {msg['recipient']}")
                        logger.info(f"  - Type: {msg['type']}")
                        logger.info(f"  - Content: {msg['message']}")
                        if msg['type'] == 'interactive':
                            logger.info(f"  - Buttons: {msg['buttons']}")
                    return True
                else:
                    logger.info("No messages would have been sent")
                    return True
            else:
                logger.error(f"Failed to process {reminder_type} reminders")
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
            logger.info(f"Triggering {reminder_type} reminders directly")
            trigger_direct_reminders(reminder_type)
        elif not has_eligible_users:
            logger.info("No eligible users found. No reminders will be sent.")
            logger.info("Run 'create_backdated_checkin.py morning' to create a backdated check-in")
        elif check_only:
            logger.info("Check-only mode - not triggering reminders")
            logger.info("Run without --check to trigger reminders") 