from app.models.user import User
from app.models.checkin import CheckIn
from app.services.whatsapp import get_whatsapp_service
from app.services.tasks import get_task_service
from flask import current_app
from datetime import datetime, timedelta
import logging

# Set up logger
logger = logging.getLogger(__name__)

def send_daily_tasks():
    """Send daily task prompts to all users from both accounts based on their check-in responses"""
    logger.info("Running daily tasks cron job")
    
    # Get all users
    users = User.get_all()
    
    if not users:
        logger.info("No users found for daily tasks")
        return
    
    # Group users by account
    users_by_account = {}
    for user in users:
        account_index = user.account_index
        if account_index not in users_by_account:
            users_by_account[account_index] = []
        users_by_account[account_index].append(user)
    
    # Time threshold for recent check-ins (last 12 hours)
    time_threshold = datetime.now() - timedelta(hours=12)
    
    # Sentiment thresholds
    positive_threshold = current_app.config.get('SENTIMENT_THRESHOLD_POSITIVE', 0.5)
    negative_threshold = current_app.config.get('SENTIMENT_THRESHOLD_NEGATIVE', -0.2)
    
    # Process each account
    for account_index, account_users in users_by_account.items():
        # Get the WhatsApp service for this account
        whatsapp_service = get_whatsapp_service(account_index)
        
        # Process each user in this account
        for user in account_users:
            try:
                # Get the user's most recent check-in
                recent_checkins = CheckIn.get_for_user(user.user_id, CheckIn.TYPE_DAILY, limit=1)
                
                if not recent_checkins:
                    logger.info(f"No recent check-ins found for user {user.user_id} (account {account_index})")
                    # Send default message for users without recent check-ins
                    whatsapp_service.send_message(
                        user.user_id,
                        "What tasks would you like to focus on today?"
                    )
                    continue
                
                recent_checkin = recent_checkins[0]
                
                # Skip if check-in is too old
                if recent_checkin.created_at < time_threshold:
                    logger.info(f"Check-in for user {user.user_id} is too old, skipping")
                    continue
                
                # Process based on sentiment
                sentiment_score = recent_checkin.sentiment_score
                
                if sentiment_score is None:
                    # Send default message if no sentiment score
                    whatsapp_service.send_message(
                        user.user_id,
                        "What tasks would you like to focus on today?"
                    )
                
                elif sentiment_score < negative_threshold:
                    # Negative sentiment - send simplified options
                    buttons = [
                        {
                            "id": "one_task",
                            "title": "One Small Task"
                        },
                        {
                            "id": "rest_today",
                            "title": "Rest Today"
                        }
                    ]
                    
                    whatsapp_service.send_interactive_message(
                        user.user_id,
                        "Task Planning",
                        "It seems you're having a tough day. Would you like to focus on just one small task, or would you prefer to rest today?",
                        buttons
                    )
                
                else:
                    # Positive or neutral sentiment - ask for tasks
                    whatsapp_service.send_message(
                        user.user_id,
                        "What tasks would you like to focus on today? You can list 1-3 tasks."
                    )
                
                logger.info(f"Successfully processed daily tasks for user {user.user_id} (account {account_index})")
            
            except Exception as e:
                logger.error(f"Error processing daily tasks for user {user.user_id}: {e}") 