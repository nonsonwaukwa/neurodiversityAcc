#!/usr/bin/env python3
"""
Midday Reminder Test

This script tests the midday reminder functionality by directly calling the send_checkin_reminders
function with the midday reminder type.
"""

import logging
from datetime import datetime, timezone, timedelta
from app import create_app
from app.cron.reminders import send_checkin_reminders, _send_reminder_if_needed
from app.models.user import User
from app.services.whatsapp import get_whatsapp_service

# Configure logging to show detailed information
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

# User ID to check
TARGET_USER_ID = "2348023672476"

# Create mocks for dependent services
class MockAnalyticsService:
    @staticmethod
    def get_sentiment_trend(user_id, days=14):
        return {"trend": "neutral", "average": 0, "samples": 0}

class MockTaskService:
    @staticmethod
    def get_self_care_tip():
        return "Take a few deep breaths and allow yourself to simply be present in this moment."

def test_reminder_eligibility():
    """Test if a user is eligible for reminders without actually sending them"""
    logger.info("="*80)
    logger.info("TESTING REMINDER ELIGIBILITY")
    logger.info("="*80)

    # Get the user
    user = User.get(TARGET_USER_ID)
    if not user:
        logger.error(f"User {TARGET_USER_ID} not found!")
        return
    
    logger.info(f"Found user: {user.name} (ID: {TARGET_USER_ID})")
    
    # Create a fake WhatsApp service to avoid actually sending messages
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
            logger.info(f"[FAKE] Would send interactive message to {recipient}: {message}")
            return {'success': True}
            
        def send_message(self, recipient, message):
            self.messages.append({
                'recipient': recipient,
                'message': message,
                'type': 'text'
            })
            logger.info(f"[FAKE] Would send text message to {recipient}: {message}")
            return {'success': True}
    
    # Use our fake service
    fake_service = FakeWhatsAppService()
    
    # Mock the analytics and task services
    from unittest.mock import patch
    
    # Create a direct test for midday reminder eligibility
    with patch('app.cron.reminders.get_analytics_service', return_value=MockAnalyticsService()), \
         patch('app.cron.reminders.get_task_service', return_value=MockTaskService()):
    
        # Test specific reminder types
        reminder_types = ['morning', 'midday', 'evening', 'nextday', None]
        
        for reminder_type in reminder_types:
            logger.info("-"*50)
            logger.info(f"Testing reminder type: {reminder_type or 'all'}")
            logger.info("-"*50)
            
            # Call the reminder function with our fake service
            _send_reminder_if_needed(user, fake_service, reminder_type)
    
    # Check if any reminders would have been sent
    if fake_service.messages:
        logger.info("="*80)
        logger.info(f"Would have sent {len(fake_service.messages)} messages")
        for idx, msg in enumerate(fake_service.messages):
            logger.info(f"Message {idx+1}:")
            logger.info(f"Type: {msg['type']}")
            logger.info(f"Recipient: {msg['recipient']}")
            logger.info(f"Content: {msg['message'][:100]}...")
            if msg['type'] == 'interactive':
                logger.info(f"Buttons: {msg['buttons']}")
            logger.info("-"*50)
    else:
        logger.info("="*80)
        logger.info("NO MESSAGES WOULD BE SENT")
        logger.info("User is not eligible for any reminders at this time")
        
    return bool(fake_service.messages)

def test_send_midday_reminder():
    """Test sending midday reminders by calling the function directly"""
    logger.info("="*80)
    logger.info("TESTING MIDDAY REMINDER")
    logger.info("="*80)
    
    now = datetime.now(timezone.utc)
    logger.info(f"Current time (UTC): {now.isoformat()}")
    
    # Calculate when midday reminder would be due
    latest_system_time = None
    
    # Get the latest system message
    user = User.get(TARGET_USER_ID)
    if user:
        from app.models.checkin import CheckIn
        last_checkins = CheckIn.get_for_user(TARGET_USER_ID, limit=2, is_response=False)
        if last_checkins:
            last_checkin = last_checkins[0]
            checkin_time = last_checkin.created_at
            if checkin_time:
                if checkin_time.tzinfo is None:
                    checkin_time = checkin_time.replace(tzinfo=timezone.utc)
                latest_system_time = checkin_time
                
                # Calculate when we'll be eligible
                midday_start = latest_system_time + timedelta(hours=3.5)
                midday_end = latest_system_time + timedelta(hours=4.5)
                
                logger.info(f"Latest system message: {latest_system_time.isoformat()}")
                logger.info(f"Midday window starts: {midday_start.isoformat()}")
                logger.info(f"Midday window ends: {midday_end.isoformat()}")
                
                time_until_window = midday_start - now
                if time_until_window.total_seconds() > 0:
                    logger.info(f"Time until midday window: {time_until_window}")
                else:
                    time_since_window = now - midday_start
                    logger.info(f"Time since midday window started: {time_since_window}")
                    
                    if now > midday_end:
                        time_since_end = now - midday_end
                        logger.info(f"Midday window has passed: {time_since_end} ago")
    
    # Call the actual reminder function with mocked services
    from unittest.mock import patch, MagicMock
    
    # Create our fake WhatsApp service
    fake_service = MagicMock()
    fake_service.send_interactive_buttons.return_value = {"success": True}
    fake_service.send_message.return_value = {"success": True}
    
    with patch('app.services.whatsapp.get_whatsapp_service', return_value=fake_service), \
         patch('app.cron.reminders.get_analytics_service', return_value=MockAnalyticsService()), \
         patch('app.cron.reminders.get_task_service', return_value=MockTaskService()):
        
        logger.info("Calling send_checkin_reminders with midday type...")
        send_checkin_reminders(reminder_type='midday')
        
        # Check if any messages would have been sent
        if fake_service.send_interactive_buttons.called or fake_service.send_message.called:
            logger.info("MESSAGES WOULD HAVE BEEN SENT:")
            
            if fake_service.send_interactive_buttons.called:
                call_count = fake_service.send_interactive_buttons.call_count
                logger.info(f"Interactive messages: {call_count}")
                for i, call in enumerate(fake_service.send_interactive_buttons.call_args_list):
                    args, kwargs = call
                    logger.info(f"Message {i+1} to {args[0]}: {args[1][:100]}...")
            
            if fake_service.send_message.called:
                call_count = fake_service.send_message.call_count
                logger.info(f"Text messages: {call_count}")
                for i, call in enumerate(fake_service.send_message.call_args_list):
                    args, kwargs = call
                    logger.info(f"Message {i+1} to {args[0]}: {args[1][:100]}...")
        else:
            logger.info("NO MESSAGES WOULD HAVE BEEN SENT")
            logger.info("No users were found eligible for midday reminders")
    
    logger.info("="*80)
    logger.info(f"Completed midday reminder test")
    logger.info("="*80)

if __name__ == "__main__":
    # Create Flask app and set up application context
    app = create_app()
    with app.app_context():
        # Test direct eligibility first
        eligibility_result = test_reminder_eligibility()
        
        # If eligible, test the full reminder function
        if eligibility_result:
            logger.info("User is eligible - testing full reminder functionality")
            test_send_midday_reminder()
        else:
            logger.info("User is NOT eligible for any reminders at this time")
            logger.info("="*80)
            logger.info("TEST MIDDAY REMINDER FUNCTION ANYWAY")
            logger.info("="*80)
            test_send_midday_reminder() 