import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models.user import User
from app.models.task import Task
from app.models.checkin import CheckIn
from app.services.whatsapp import get_whatsapp_service
from app.services.analytics import get_analytics_service
from app.services.tasks import get_task_service
import logging
from datetime import datetime, timedelta, timezone
from flask import current_app

# Set up logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Set to DEBUG level

# Add a console handler if not present
if not logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

# Create Flask app and context
app = create_app()
app.app_context().push()

def send_checkin_reminders(reminder_type=None):
    """
    Send reminders to users who haven't responded to their check-ins
    
    Args:
        reminder_type (str, optional): Type of reminder to send ('morning', 'midday', 'evening', 'nextday').
                                      If None, checks all reminder types based on time since check-in.
    """
    logger.info(f"Running check-in reminder cron job for type: {reminder_type or 'all'}")
    
    try:
        # Get all active users
        users = User.get_all_active()
        logger.debug(f"Found {len(users) if users else 0} active users")
        
        if not users:
            logger.info("No active users found for reminders")
            return
        
        # Group users by account
        users_by_account = {}
        for user in users:
            account_index = user.account_index
            if account_index not in users_by_account:
                users_by_account[account_index] = []
            users_by_account[account_index].append(user)
        
        logger.debug(f"Grouped users into {len(users_by_account)} accounts")
        
        # Process each account
        for account_index, account_users in users_by_account.items():
            # Get the WhatsApp service for this account
            whatsapp_service = get_whatsapp_service(account_index)
            logger.debug(f"Processing {len(account_users)} users for account {account_index}")
            
            # Process each user in this account
            for user in account_users:
                try:
                    _send_reminder_if_needed(user, whatsapp_service, reminder_type)
                except Exception as e:
                    logger.error(f"Error sending reminder to user {user.user_id}: {e}", exc_info=True)

    except Exception as e:
        logger.error(f"Unexpected error in reminders: {e}", exc_info=True)

def _send_reminder_if_needed(user, whatsapp_service, reminder_type=None):
    """
    Check if a user needs a reminder and send if appropriate
    
    Args:
        user (User): The user to check
        whatsapp_service (WhatsAppService): The WhatsApp service instance
        reminder_type (str, optional): Type of reminder to send ('morning', 'midday', 'evening', 'nextday')
    """
    logger.info(f"Checking reminder eligibility for user {user.user_id}")
    
    # Get the user's last check-in (sent by system)
    last_checkins = CheckIn.get_for_user(
        user_id=user.user_id,
        limit=2,
        is_response=False
    )
    
    if not last_checkins:
        logger.info(f"No check-ins found for user {user.user_id}")
        return  # No check-ins found
    
    last_checkin = last_checkins[0]
    logger.debug(f"Last check-in time for user {user.user_id}: {last_checkin.created_at}")
    
    # Get the user's last response
    last_responses = CheckIn.get_for_user(
        user_id=user.user_id,
        limit=2,
        is_response=True
    )
    
    if last_responses:
        logger.debug(f"Last response time for user {user.user_id}: {last_responses[0].created_at}")
    else:
        logger.debug(f"No responses found for user {user.user_id}")
    
    # Ensure last_checkin.created_at is timezone-aware
    checkin_time = last_checkin.created_at
    if checkin_time is None:
        logger.warning(f"Check-in has no created_at timestamp for user {user.user_id}")
        return
    
    if checkin_time.tzinfo is None:
        # If naive datetime, assume it's in UTC
        checkin_time = checkin_time.replace(tzinfo=timezone.utc)
        logger.debug(f"Added UTC timezone to naive check-in datetime: {checkin_time.isoformat()}")
    
    # If user's last response is newer than our last check-in, they've responded already
    if last_responses and last_responses[0].created_at:
        response_time = last_responses[0].created_at
        if response_time.tzinfo is None:
            response_time = response_time.replace(tzinfo=timezone.utc)
            
        if response_time > checkin_time:
            logger.info(f"User {user.user_id} already responded to latest check-in")
            return
    
    # Calculate time since last check-in with timezone-aware datetimes
    now = datetime.now(timezone.utc)
    logger.debug(f"Current time (UTC): {now.isoformat()}")
    
    time_since_checkin = now - checkin_time
    logger.debug(f"Time since last check-in for user {user.user_id}: {time_since_checkin}")

    # Get analytics about the user
    analytics_service = get_analytics_service()
    sentiment_trend = analytics_service.get_sentiment_trend(user.user_id)
    task_service = get_task_service()

    # First Follow-up (12:30 PM, 2 hours after check-in)
    if (reminder_type == 'morning' or reminder_type is None) and timedelta(hours=1.5) < time_since_checkin <= timedelta(hours=2.5):
        logger.info(f"User {user.user_id} eligible for morning reminder (first follow-up)")
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
        try:
            whatsapp_service.send_interactive_buttons(user.user_id, message, buttons)
            logger.info(f"Sent first follow-up to {user.user_id}")
        except Exception as e:
            logger.error(f"Failed to send morning reminder to {user.user_id}: {str(e)}")

    # Mid-day Check (2:30 PM, 4 hours after check-in)
    elif (reminder_type == 'midday' or reminder_type is None) and timedelta(hours=3.5) < time_since_checkin <= timedelta(hours=4.5):
        logger.info(f"User {user.user_id} eligible for mid-day check")
        message = (
            f"Hi {user.name}! 🌤️ The day still holds possibilities, and that's wonderful. "
            f"If it feels right for you, maybe you'd like to:"
        )
        buttons = [
            {"id": "plan_afternoon", "title": "Plan afternoon"},
            {"id": "self_care", "title": "Self-care time"},
            {"id": "just_chat", "title": "Just chat"}
        ]
        try:
            whatsapp_service.send_interactive_buttons(user.user_id, message, buttons)
            logger.info(f"Sent mid-day check to {user.user_id}")
        except Exception as e:
            logger.error(f"Failed to send midday reminder to {user.user_id}: {str(e)}")

    # Evening Reset (6:30 PM, 8 hours after check-in)
    elif (reminder_type == 'evening' or reminder_type is None) and timedelta(hours=7.5) < time_since_checkin <= timedelta(hours=8.5):
        logger.info(f"User {user.user_id} eligible for evening reset")
        # Get a self-care tip
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
        try:
            whatsapp_service.send_interactive_buttons(user.user_id, message, buttons)
            logger.info(f"Sent evening reset to {user.user_id}")
        except Exception as e:
            logger.error(f"Failed to send evening reminder to {user.user_id}: {str(e)}")

    # Next Day Support (>24 hours)
    # This is handled separately as it's not tied to a specific time of day
    elif (reminder_type == 'nextday' or reminder_type is None) and time_since_checkin > timedelta(hours=24):
        logger.info(f"User {user.user_id} eligible for next-day support")
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
        try:
            whatsapp_service.send_interactive_buttons(user.user_id, message, buttons)
            logger.info(f"Sent next-day support message to {user.user_id}")
        except Exception as e:
            logger.error(f"Failed to send next-day reminder to {user.user_id}: {str(e)}")
    else:
        logger.info(f"User {user.user_id} is not in any reminder window at the moment")

def handle_reminder_response(user, response_type):
    """
    Handle responses to reminder messages
    
    Args:
        user (User): The user who responded
        response_type (str): The type of response received
    """
    whatsapp_service = get_whatsapp_service(user.account_index)
    task_service = get_task_service()
    current_hour = datetime.now(timezone.utc).hour  # Use timezone-aware datetime

    if response_type == "plan_day":
        if current_hour < 12:  # Morning
            message = "Let's gently plan your day in a way that feels good to you. What might you like to focus on today? You could share up to 3 things if that feels comfortable, or just 1 is perfectly fine too."
        else:  # Afternoon
            message = "Let's think about the rest of your day in a way that feels nurturing. What's one small thing you might like to focus on? Even the tiniest step counts."
        whatsapp_service.send_message(user.user_id, message)

    elif response_type == "quick_checkin":
        message = "How are you feeling in this moment? This is just a soft check-in - no pressure at all to plan anything. Your wellbeing matters most."
        whatsapp_service.send_message(user.user_id, message)

    elif response_type == "remind_later":
        message = "Of course! I'll give you some space and maybe check in a bit later. Take all the time you need. 💫"
        whatsapp_service.send_message(user.user_id, message)

    elif response_type == "self_care":
        self_care_tip = task_service.get_self_care_tip()
        message = f"Taking care of yourself is so important and something to be proud of. Here's a gentle suggestion if it resonates with you: {self_care_tip} 💝"
        whatsapp_service.send_message(user.user_id, message)

    elif response_type == "plan_tomorrow":
        message = (
            "Let's think softly about tomorrow. No pressure to plan everything - "
            "even setting one small, kind intention for tomorrow can be nurturing. "
            "What might feel manageable and good for you?"
        )
        whatsapp_service.send_message(user.user_id, message)

    elif response_type == "fresh_start":
        message = (
            "Every moment offers a chance for a gentle fresh start! "
            "Would you like to consider something small for today, or maybe look ahead to tomorrow? "
            "Whatever feels most nurturing for you right now."
        )
        buttons = [
            {"id": "plan_today", "title": "Something for today"},
            {"id": "plan_tomorrow", "title": "Think about tomorrow"}
        ]
        whatsapp_service.send_interactive_buttons(user.user_id, message, buttons)

    elif response_type == "need_help":
        message = (
            "I'm here with you with warmth and care. Sometimes things feel overwhelming, and that's completely understandable. "
            "Would any of these feel supportive right now?"
        )
        buttons = [
            {"id": "simplify_tasks", "title": "Simplify things"},
            {"id": "just_talk", "title": "Just chat"},
            {"id": "get_strategies", "title": "Gentle strategies"}
        ]
        whatsapp_service.send_interactive_buttons(user.user_id, message, buttons)

    logger.info(f"Handled reminder response '{response_type}' for user {user.user_id}")

if __name__ == "__main__":
    send_checkin_reminders() 