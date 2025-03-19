import logging
from datetime import datetime, timedelta
from app.models.user import User
from app.models.checkin import CheckIn
from app.services.whatsapp import get_whatsapp_service
from app.services.analytics import get_analytics_service
from app.services.tasks import get_task_service

logger = logging.getLogger(__name__)

def send_checkin_reminders(reminder_type=None):
    """
    Send reminders to users who haven't responded to their check-ins
    
    Args:
        reminder_type (str, optional): Type of reminder to send ('morning', 'midday', 'evening').
                                      If None, checks all reminder types based on time since check-in.
    """
    logger.info(f"Running check-in reminder cron job for type: {reminder_type or 'all'}")
    
    # Get all active users
    users = User.get_all_active()
    
    # Group users by account
    users_by_account = {}
    for user in users:
        account_index = user.account_index
        if account_index not in users_by_account:
            users_by_account[account_index] = []
        users_by_account[account_index].append(user)
    
    # Process each account
    for account_index, account_users in users_by_account.items():
        # Get the WhatsApp service for this account
        whatsapp_service = get_whatsapp_service(account_index)
        
        # Process each user in this account
        for user in account_users:
            try:
                _send_reminder_if_needed(user, whatsapp_service, reminder_type)
            except Exception as e:
                logger.error(f"Error sending reminder to user {user.user_id}: {e}")

def _send_reminder_if_needed(user, whatsapp_service, reminder_type=None):
    """
    Check if a user needs a reminder and send if appropriate
    
    Args:
        user (User): The user to check
        whatsapp_service (WhatsAppService): The WhatsApp service instance
        reminder_type (str, optional): Type of reminder to send ('morning', 'midday', 'evening')
    """
    # Get the user's last check-in (sent by system)
    last_checkins = CheckIn.get_for_user(user.user_id, limit=2, is_response=False)
    
    if not last_checkins:
        return  # No check-ins found
    
    last_checkin = last_checkins[0]
    
    # Get the user's last response
    last_responses = CheckIn.get_for_user(user.user_id, limit=2, is_response=True)
    
    # If user's last response is newer than our last check-in, they've responded already
    if last_responses and last_responses[0].created_at > last_checkin.created_at:
        return
    
    # Calculate time since last check-in
    time_since_checkin = datetime.now() - last_checkin.created_at
    current_hour = datetime.now().hour

    # Get analytics about the user
    analytics_service = get_analytics_service()
    sentiment_trend = analytics_service.get_sentiment_trend(user.user_id)
    task_service = get_task_service()

    # First Follow-up (12:30 PM, 2 hours after check-in)
    if (reminder_type == 'morning' or reminder_type is None) and timedelta(hours=1.5) < time_since_checkin <= timedelta(hours=2.5):
        message = (
            f"Hey {user.name}! No pressure at all - I'm still here when you're ready to plan your day. "
            f"Would you like to:"
        )
        buttons = [
            {"id": "plan_day", "title": "Plan my day"},
            {"id": "quick_checkin", "title": "Quick check-in"},
            {"id": "remind_later", "title": "Remind me later"}
        ]
        whatsapp_service.send_interactive_buttons(user.user_id, message, buttons)
        logger.info(f"Sent first follow-up to {user.user_id}")

    # Mid-day Check (2:30 PM, 4 hours after check-in)
    elif (reminder_type == 'midday' or reminder_type is None) and timedelta(hours=3.5) < time_since_checkin <= timedelta(hours=4.5):
        message = (
            f"Hi {user.name}! The day is still young. "
            f"Would you like to:"
        )
        buttons = [
            {"id": "plan_afternoon", "title": "Plan afternoon"},
            {"id": "self_care", "title": "Focus on self-care"},
            {"id": "just_chat", "title": "Just chat"}
        ]
        whatsapp_service.send_interactive_buttons(user.user_id, message, buttons)
        logger.info(f"Sent mid-day check to {user.user_id}")

    # Evening Reset (6:30 PM, 8 hours after check-in)
    elif (reminder_type == 'evening' or reminder_type is None) and timedelta(hours=7.5) < time_since_checkin <= timedelta(hours=8.5):
        # Get a self-care tip
        self_care_tip = task_service.get_self_care_tip()
        
        message = (
            f"Hey {user.name}! How has your day been? Remember, every day is a fresh start. "
            f"Here's a gentle self-care reminder: {self_care_tip}\n\n"
            f"Would you like to:"
        )
        buttons = [
            {"id": "share_day", "title": "Share about today"},
            {"id": "plan_tomorrow", "title": "Plan tomorrow"},
            {"id": "rest_now", "title": "Rest now"}
        ]
        whatsapp_service.send_interactive_buttons(user.user_id, message, buttons)
        logger.info(f"Sent evening reset to {user.user_id}")

    # Next Day Support (>24 hours)
    # This is handled separately as it's not tied to a specific time of day
    elif time_since_checkin > timedelta(hours=24):
        message = (
            f"Hi {user.name}, I've noticed we haven't connected in a bit, and that's completely okay! "
            f"Sometimes we need space, and I'm here whenever you're ready. "
            f"Would you like to:"
        )
        buttons = [
            {"id": "fresh_start", "title": "Fresh start"},
            {"id": "gentle_checkin", "title": "Just say hi"},
            {"id": "need_help", "title": "Need support"}
        ]
        whatsapp_service.send_interactive_buttons(user.user_id, message, buttons)
        logger.info(f"Sent next-day support message to {user.user_id}")

def handle_reminder_response(user, response_type):
    """
    Handle responses to reminder messages
    
    Args:
        user (User): The user who responded
        response_type (str): The type of response received
    """
    whatsapp_service = get_whatsapp_service(user.account_index)
    task_service = get_task_service()
    current_hour = datetime.now().hour

    if response_type == "plan_day":
        if current_hour < 12:  # Morning
            message = "Let's plan your day! What would you like to focus on today? You can list up to 3 tasks."
        else:  # Afternoon
            message = "Let's plan the rest of your day. What's one thing you'd like to accomplish?"
        whatsapp_service.send_message(user.user_id, message)

    elif response_type == "quick_checkin":
        message = "How are you feeling right now? Just a quick check-in - no pressure to plan anything."
        whatsapp_service.send_message(user.user_id, message)

    elif response_type == "remind_later":
        message = "No problem! I'll check in with you a bit later. Take care!"
        whatsapp_service.send_message(user.user_id, message)

    elif response_type == "self_care":
        self_care_tip = task_service.get_self_care_tip()
        message = f"Taking care of yourself is important! Here's a suggestion: {self_care_tip}"
        whatsapp_service.send_message(user.user_id, message)

    elif response_type == "plan_tomorrow":
        message = (
            "Let's think about tomorrow. No pressure to plan everything - "
            "even one small intention for tomorrow can help. What feels manageable?"
        )
        whatsapp_service.send_message(user.user_id, message)

    elif response_type == "fresh_start":
        message = (
            "Every moment is a chance to start fresh! "
            "Would you like to plan something small for today, or shall we look ahead to tomorrow?"
        )
        buttons = [
            {"id": "plan_today", "title": "Plan today"},
            {"id": "plan_tomorrow", "title": "Plan tomorrow"}
        ]
        whatsapp_service.send_interactive_buttons(user.user_id, message, buttons)

    elif response_type == "need_help":
        message = (
            "I'm here to support you. Sometimes things get overwhelming, and that's okay. "
            "Would you like to:"
        )
        buttons = [
            {"id": "simplify_tasks", "title": "Simplify tasks"},
            {"id": "just_talk", "title": "Just talk"},
            {"id": "get_strategies", "title": "Get strategies"}
        ]
        whatsapp_service.send_interactive_buttons(user.user_id, message, buttons)

    logger.info(f"Handled reminder response '{response_type}' for user {user.user_id}") 