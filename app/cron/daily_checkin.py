from app.models.user import User
from app.models.task import Task
from app.services.whatsapp import get_whatsapp_service
from datetime import datetime
import logging

# Set up logger
logger = logging.getLogger(__name__)

def send_daily_checkin():
    """Send daily check-in messages to all users from both accounts"""
    logger.info("Running daily check-in cron job")
    
    # Get all users
    users = User.get_all()
    
    if not users:
        logger.info("No users found for daily check-in")
        return
    
    # Group users by account
    users_by_account = {}
    for user in users:
        account_index = user.account_index
        if account_index not in users_by_account:
            users_by_account[account_index] = []
        users_by_account[account_index].append(user)
    
    # Get today's date (for task scheduling)
    today = datetime.now()
    
    # Process each account
    for account_index, account_users in users_by_account.items():
        # Get the WhatsApp service for this account
        whatsapp_service = get_whatsapp_service(account_index)
        
        # Process each user in this account
        for user in account_users:
            try:
                # Format the message with the user's name
                name = user.name.split('_')[0] if '_' in user.name else user.name
                checkin_message = f"Good morning {name}! How are you feeling today?"
                
                logger.info(f"Sending daily check-in to user {user.user_id} (account {account_index})")
                response = whatsapp_service.send_message(user.user_id, checkin_message)
                
                if response:
                    logger.info(f"Successfully sent daily check-in to user {user.user_id}")
                else:
                    logger.error(f"Failed to send daily check-in to user {user.user_id}")
            
            except Exception as e:
                logger.error(f"Error sending daily check-in to user {user.user_id}: {e}")

def process_daily_response(user, message_text, sentiment_score):
    """
    Process the response to a daily check-in
    
    Args:
        user (User): The user who responded
        message_text (str): The message text
        sentiment_score (float): The sentiment score of the message
    """
    logger.info(f"Processing daily check-in response for user {user.user_id}")
    whatsapp_service = get_whatsapp_service(user.account_index)
    
    # Handle based on sentiment and planning type
    if sentiment_score < -0.3:  # Negative sentiment
        # For both planning types, offer simplified options when feeling overwhelmed
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
            "Daily Planning",
            "It seems you're having a tough day. Would you like to focus on just one small task, or would you prefer to rest today?",
            buttons
        )
    else:  # Neutral or positive sentiment
        if user.planning_type == 'weekly':
            # For weekly planners, show today's scheduled tasks
            today = datetime.now()
            tasks = Task.get_for_user(user.user_id, scheduled_date=today)
            
            if tasks:
                task_list = "\n".join([f"- {task.description}" for task in tasks])
                message = f"Here are your tasks for today:\n{task_list}\n\nHow would you like to proceed with these tasks?"
                whatsapp_service.send_message(user.user_id, message)
            else:
                message = "You don't have any tasks scheduled for today. Would you like to add some tasks for today?"
                whatsapp_service.send_message(user.user_id, message)
        else:  # Daily planner
            # For daily planners, ask for daily tasks
            whatsapp_service.send_message(
                user.user_id,
                "What tasks would you like to focus on today? You can list 1-3 tasks."
            )
    
    logger.info(f"Processed daily check-in for user {user.user_id} with sentiment {sentiment_score}")

def handle_one_task_request(user):
    """
    Handle a request for one small task
    
    Args:
        user (User): The user
    """
    whatsapp_service = get_whatsapp_service(user.account_index)
    whatsapp_service.send_message(user.user_id, "What's one small thing you'd like to accomplish today?")

def handle_rest_request(user):
    """
    Handle a request to rest
    
    Args:
        user (User): The user
    """
    whatsapp_service = get_whatsapp_service(user.account_index)
    whatsapp_service.send_message(
        user.user_id, 
        "That's absolutely fine. Rest is important. I'll check in with you tomorrow."
    ) 