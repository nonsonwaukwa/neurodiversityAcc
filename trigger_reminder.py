#!/usr/bin/env python3
"""
Manual Reminder Trigger Script

This script manually triggers a reminder for a specific user who hasn't responded to check-ins.
It bypasses the normal reminder windows to ensure the user receives a follow-up message.
"""

import logging
import sys
from app import create_app
from app.models.user import User
from app.models.checkin import CheckIn
from app.services.whatsapp import get_whatsapp_service
from datetime import datetime, timezone

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def trigger_manual_reminder(user_id, reminder_type=None):
    """
    Manually trigger a reminder for a specific user regardless of time window
    
    Args:
        user_id (str): The WhatsApp number of the user to send the reminder to
        reminder_type (str, optional): Type of reminder to send ('morning', 'midday', 'evening', 'nextday')
    """
    try:
        # Get the user
        user = User.get(user_id)
        if not user:
            logger.error(f"User with ID {user_id} not found")
            return False
        
        # Get the user's WhatsApp service
        whatsapp_service = get_whatsapp_service(user.account_index)
        
        # Get the user's last check-in
        last_checkins = CheckIn.get_for_user(user.user_id, limit=2, is_response=False)
        if not last_checkins:
            logger.error(f"No check-ins found for user {user.user_id}")
            return False
        
        last_checkin = last_checkins[0]
        logger.info(f"Last check-in for user {user.user_id} was at {last_checkin.created_at}")
        
        # Determine which reminder to send
        if reminder_type == 'morning' or reminder_type is None:
            message = (
                f"Hey {user.name}! 💫 Just a gentle check-in - absolutely no pressure at all. "
                f"I'm still here whenever you feel ready to connect. "
                f"If you'd like, you could:"
            )
            buttons = [
                {"id": "plan_day", "title": "Plan my day"},
                {"id": "quick_checkin", "title": "Quick hello"},
                {"id": "remind_later", "title": "Not just now"}
            ]
            whatsapp_service.send_interactive_buttons(user.user_id, message, buttons)
            logger.info(f"Sent first follow-up to {user.user_id}")
            
        elif reminder_type == 'midday':
            message = (
                f"Hi {user.name}! 🌤️ The day still holds possibilities, and that's wonderful. "
                f"If it feels right for you, maybe you'd like to:"
            )
            buttons = [
                {"id": "plan_afternoon", "title": "Plan afternoon"},
                {"id": "self_care", "title": "Self-care time"},
                {"id": "just_chat", "title": "Just chat"}
            ]
            whatsapp_service.send_interactive_buttons(user.user_id, message, buttons)
            logger.info(f"Sent mid-day check to {user.user_id}")
            
        elif reminder_type == 'evening':
            # Get a self-care tip
            from app.services.tasks import get_task_service
            task_service = get_task_service()
            self_care_tip = task_service.get_self_care_tip()
            
            message = (
                f"Hey {user.name}! ✨ How has your day unfolded? Remember, each day is its own journey, "
                f"and tomorrow offers a fresh beginning whenever you need it.\n\n"
                f"Here's a gentle self-care reminder if it feels helpful: {self_care_tip}\n\n"
                f"If you'd like, you could:"
            )
            buttons = [
                {"id": "share_day", "title": "Share about today"},
                {"id": "plan_tomorrow", "title": "Gentle tomorrow plan"},
                {"id": "rest_now", "title": "Rest & recharge"}
            ]
            whatsapp_service.send_interactive_buttons(user.user_id, message, buttons)
            logger.info(f"Sent evening reset to {user.user_id}")
            
        elif reminder_type == 'nextday':
            message = (
                f"Hi {user.name} 💖, I've noticed we haven't connected in a little while, and that's completely okay! "
                f"Sometimes we need space or things get busy, and I'm here with warmth whenever you're ready. "
                f"No rush at all. If you'd like to reconnect, maybe you'd enjoy:"
            )
            buttons = [
                {"id": "fresh_start", "title": "Fresh beginning"},
                {"id": "gentle_checkin", "title": "Just say hi"},
                {"id": "need_help", "title": "Gentle support"}
            ]
            whatsapp_service.send_interactive_buttons(user.user_id, message, buttons)
            logger.info(f"Sent next-day support message to {user.user_id}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error sending manual reminder: {str(e)}", exc_info=True)
        return False

if __name__ == "__main__":
    # Default user ID from our diagnostic script
    user_id = "2348023672476"
    
    # Default to morning reminder
    reminder_type = "morning"
    
    # Parse command line arguments if provided
    if len(sys.argv) > 1:
        user_id = sys.argv[1]
    if len(sys.argv) > 2:
        reminder_type = sys.argv[2]
    
    # Create Flask app and set up application context
    app = create_app()
    with app.app_context():
        logger.info(f"Triggering {reminder_type} reminder for user {user_id}")
        success = trigger_manual_reminder(user_id, reminder_type)
        
        if success:
            logger.info(f"Successfully sent {reminder_type} reminder to user {user_id}")
        else:
            logger.error(f"Failed to send {reminder_type} reminder to user {user_id}")
            sys.exit(1) 