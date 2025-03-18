import logging
from datetime import datetime, timedelta
from app.models.user import User
from app.models.checkin import CheckIn
from app.services.whatsapp import get_whatsapp_service
from app.services.analytics import get_analytics_service

logger = logging.getLogger(__name__)

def send_checkin_reminders():
    """Send reminders to users who haven't responded to their check-ins"""
    logger.info("Running check-in reminder cron job")
    
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
                _send_reminder_if_needed(user, whatsapp_service)
            except Exception as e:
                logger.error(f"Error sending reminder to user {user.user_id}: {e}")

def _send_reminder_if_needed(user, whatsapp_service):
    """
    Check if a user needs a reminder and send if appropriate
    
    Args:
        user (User): The user to check
        whatsapp_service (WhatsAppService): The WhatsApp service instance
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
    
    # If it's been over 3 hours but less than 12 hours, send a gentle reminder
    if timedelta(hours=3) < time_since_checkin < timedelta(hours=12):
        # Get analytics about the user
        analytics_service = get_analytics_service()
        sentiment_trend = analytics_service.get_sentiment_trend(user.user_id)
        
        # Customize message based on their sentiment trend
        if sentiment_trend["trend"] == "positive" or sentiment_trend["trend"] == "improving":
            message = (
                f"Hi {user.name}! Just checking in to see how you're doing today. "
                f"You've been making great progress lately, and I'd love to hear how things are going. "
                f"Would you like to share a quick update?"
            )
        elif sentiment_trend["trend"] == "declining":
            message = (
                f"Hi {user.name}, I noticed you haven't checked in yet today. "
                f"I know things have been challenging lately. Even on tough days, "
                f"just checking in can help us stay on track. How are you feeling?"
            )
        else:
            message = (
                f"Hi {user.name}! Just a friendly reminder to check in when you get a chance. "
                f"Even a quick check-in helps us stay connected and focused on your goals. "
                f"How's your day going so far?"
            )
        
        # Send the reminder
        whatsapp_service.send_message(user.user_id, message)
        
        # Log that a reminder was sent
        logger.info(f"Sent check-in reminder to user {user.user_id}")
    
    # If it's been more than 24 hours, send a more concerned check-in
    elif time_since_checkin > timedelta(hours=24):
        message = (
            f"Hi {user.name}, I noticed it's been a while since we last connected. "
            f"I'm here to support you on both good days and challenging ones. "
            f"Would you like to check in now, or would tomorrow be better? "
            f"Remember, small steps still count as progress."
        )
        
        # Send the reminder
        whatsapp_service.send_message(user.user_id, message)
        
        # Log that a concerned reminder was sent
        logger.info(f"Sent concerned reminder to user {user.user_id} after {time_since_checkin.days} days") 