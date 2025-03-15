from app.models.user import User
from app.services.whatsapp import get_whatsapp_service
import logging
from datetime import datetime, timedelta

# Set up logger
logger = logging.getLogger(__name__)

def send_weekly_checkin():
    """Send weekly mental check-in messages to all users and classify planning type"""
    logger.info("Running weekly check-in cron job")
    
    # Get all users
    users = User.get_all()
    
    if not users:
        logger.info("No users found for weekly check-in")
        return
    
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
                # Format the message with the user's name
                name = user.name.split('_')[0] if '_' in user.name else user.name
                
                # This check-in will be used to determine planning type
                checkin_message = f"Hey {name}, let's check in! How are you feeling about the upcoming week?"
                
                logger.info(f"Sending weekly check-in to user {user.user_id} (account {account_index})")
                response = whatsapp_service.send_message(user.user_id, checkin_message)
                
                if response:
                    logger.info(f"Successfully sent weekly check-in to user {user.user_id}")
                else:
                    logger.error(f"Failed to send weekly check-in to user {user.user_id}")
            
            except Exception as e:
                logger.error(f"Error sending weekly check-in to user {user.user_id}: {e}")

def process_weekly_response(user, message_text, sentiment_score):
    """
    Process the response to a weekly check-in and determine planning type
    
    Args:
        user (User): The user who responded
        message_text (str): The message text
        sentiment_score (float): The sentiment score of the message
    """
    logger.info(f"Processing weekly check-in response for user {user.user_id}")
    
    # Determine planning type based on sentiment
    if sentiment_score < -0.3:  # Overwhelmed/burnt out
        # Switch to daily planning
        user.update_planning_type('daily')
        logger.info(f"User {user.user_id} classified as daily planner due to low sentiment score: {sentiment_score}")
        
        # Send confirmation message
        whatsapp_service = get_whatsapp_service(user.account_index)
        message = "I understand you're feeling a bit overwhelmed. I'll help you take it day by day with more frequent check-ins and simpler planning."
        whatsapp_service.send_message(user.user_id, message)
    else:
        # Keep or switch to weekly planning
        user.update_planning_type('weekly')
        logger.info(f"User {user.user_id} classified as weekly planner with sentiment score: {sentiment_score}")
        
        # Send confirmation message
        whatsapp_service = get_whatsapp_service(user.account_index)
        message = "Sounds like you're ready to plan for the week! I'll check in each morning, but we'll focus on weekly goals."
        whatsapp_service.send_message(user.user_id, message)
    
    # Now let's prompt for tasks based on their planning type
    prompt_for_tasks(user)

def prompt_for_tasks(user):
    """
    Prompt the user for tasks based on their planning type
    
    Args:
        user (User): The user to prompt
    """
    whatsapp_service = get_whatsapp_service(user.account_index)
    
    if user.planning_type == 'weekly':
        # For weekly planners, we'll ask them to plan the whole week
        # Get the dates for the upcoming week
        today = datetime.now()
        dates = []
        for i in range(7):
            date = today + timedelta(days=i)
            dates.append(date.strftime("%A, %b %d"))
        
        dates_str = "\n".join([f"- {date}" for date in dates])
        
        message = (
            f"Let's plan your week ahead! You can send me tasks for each day of the week.\n\n"
            f"Upcoming days:\n{dates_str}\n\n"
            f"You can format your response like this:\n"
            f"Monday: Task 1, Task 2\n"
            f"Tuesday: Task 3\n"
            f"... and so on."
        )
        whatsapp_service.send_message(user.user_id, message)
    else:
        # For daily planners, we'll just focus on today
        message = "Let's just focus on today. What tasks would you like to accomplish today? You can list up to 3 tasks."
        whatsapp_service.send_message(user.user_id, message) 