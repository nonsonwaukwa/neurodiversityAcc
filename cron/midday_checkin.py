import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models.user import User
from app.models.checkin import CheckIn
from app.services.whatsapp import get_whatsapp_service
from app.services.tasks import get_task_service
from flask import current_app
from datetime import datetime, timedelta, timezone
import logging

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

def send_midday_checkin():
    """Send midday check-ins to users with active tasks to check their progress"""
    logger.info("Running midday check-in cron job")
    
    # Get all users
    users = User.get_all()
    logger.debug(f"Found {len(users) if users else 0} total users")
    
    if not users:
        logger.info("No users found for midday check-in")
        return
    
    # Group users by account
    users_by_account = {}
    for user in users:
        account_index = user.account_index
        if account_index not in users_by_account:
            users_by_account[account_index] = []
        users_by_account[account_index].append(user)
    
    logger.debug(f"Grouped users into {len(users_by_account)} accounts")
    
    # Time threshold for recent check-ins (last 6 hours)
    time_threshold = datetime.now(timezone.utc) - timedelta(hours=6)
    
    # Sentiment thresholds
    positive_threshold = current_app.config.get('SENTIMENT_THRESHOLD_POSITIVE', 0.5)
    negative_threshold = current_app.config.get('SENTIMENT_THRESHOLD_NEGATIVE', -0.2)
    
    # Process each account
    for account_index, account_users in users_by_account.items():
        # Get the WhatsApp service for this account
        whatsapp_service = get_whatsapp_service(account_index)
        logger.debug(f"Processing {len(account_users)} users for account {account_index}")
        
        # Process each user in this account
        for user in account_users:
            try:
                # Get user's active tasks
                task_service = get_task_service()
                active_tasks = task_service.get_pending_tasks(user.user_id)
                logger.debug(f"Found {len(active_tasks) if active_tasks else 0} active tasks for user {user.user_id}")
                
                if not active_tasks:
                    logger.info(f"No active tasks found for user {user.user_id}, skipping midday check-in")
                    continue
                
                # Get the user's most recent check-in
                recent_checkins = CheckIn.get_for_user(
                    user_id=user.user_id,
                    checkin_type=CheckIn.TYPE_DAILY,
                    limit=1
                )
                logger.debug(f"Found {len(recent_checkins) if recent_checkins else 0} recent check-ins for user {user.user_id}")
                
                if not recent_checkins:
                    logger.info(f"No recent check-ins found for user {user.user_id}")
                    continue
                
                recent_checkin = recent_checkins[0]
                
                # Make created_at timezone-aware if it isn't already
                if recent_checkin.created_at and recent_checkin.created_at.tzinfo is None:
                    recent_checkin.created_at = recent_checkin.created_at.replace(tzinfo=timezone.utc)
                
                # Skip if check-in is too old
                if recent_checkin.created_at < time_threshold:
                    logger.info(f"Check-in for user {user.user_id} is too old, skipping")
                    continue
                
                # Process based on sentiment
                sentiment_score = recent_checkin.sentiment_score
                logger.debug(f"Sentiment score for user {user.user_id}: {sentiment_score}")
                
                if sentiment_score is None:
                    # Default message for no sentiment score
                    logger.debug(f"Sending default message to user {user.user_id} (no sentiment score)")
                    whatsapp_service.send_message(
                        user.user_id,
                        "How are your tasks going? You can mark them as done, in progress, or stuck."
                    )
                
                elif sentiment_score < negative_threshold:
                    # Negative sentiment - offer support and simplified options
                    logger.debug(f"Sending support options to user {user.user_id} (negative sentiment)")
                    buttons = [
                        {
                            "id": "support_needed",
                            "title": "Need Support"
                        },
                        {
                            "id": "rest_today",
                            "title": "Rest Today"
                        }
                    ]
                    
                    whatsapp_service.send_interactive_message(
                        user.user_id,
                        "Task Progress Check",
                        "I notice you might be having a tough time. Would you like some support with your tasks, or would you prefer to rest today?",
                        buttons
                    )
                
                else:
                    # Positive or neutral sentiment - check task progress
                    logger.debug(f"Sending task progress check to user {user.user_id} (positive/neutral sentiment)")
                    task_list = "\n".join([f"• {task.description}" for task in active_tasks])
                    message = (
                        "How are your tasks going?\n\n"
                        f"Your active tasks:\n{task_list}\n\n"
                        "You can mark them as done, in progress, or stuck."
                    )
                    
                    whatsapp_service.send_message(user.user_id, message)
                
                logger.info(f"Successfully processed midday check-in for user {user.user_id} (account {account_index})")
            
            except Exception as e:
                logger.error(f"Error processing midday check-in for user {user.user_id}: {e}", exc_info=True)

if __name__ == "__main__":
    send_midday_checkin() 