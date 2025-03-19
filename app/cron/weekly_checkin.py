from app.models.user import User
from app.models.task import Task
from app.models.checkin import CheckIn
from app.services.whatsapp import get_whatsapp_service
from app.services.tasks import get_task_service
import logging
from datetime import datetime, timedelta
import re

# Set up logger
logger = logging.getLogger(__name__)

def send_weekly_checkin():
    """Send weekly mental check-in messages to all users and classify planning type"""
    logger.info("Running weekly check-in cron job")
    
    # Get all users that have been in the system for at least a week
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
                checkin_message = f"Hello {name} 💫 A gentle check-in about the week ahead - how are you feeling as we begin this new week? Whatever you're experiencing is welcome here."
                
                logger.info(f"Sending weekly check-in to user {user.user_id} (account {account_index})")
                response = whatsapp_service.send_message(user.user_id, checkin_message)
                
                # Store this message as a check-in
                CheckIn.create(user.user_id, checkin_message, CheckIn.TYPE_WEEKLY)
                
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
    whatsapp_service = get_whatsapp_service(user.account_index)
    
    # Determine planning type based on sentiment
    if sentiment_score < -0.3:  # Overwhelmed/burnt out
        # Switch to daily planning
        user.update_planning_type('daily')
        logger.info(f"User {user.user_id} classified as daily planner due to low sentiment score: {sentiment_score}")
        
        # Send confirmation message
        message = "I hear that things might be feeling a bit much right now, and that's completely understandable. 💜 We can take it day by day with gentler check-ins and simpler planning - one small step at a time."
        whatsapp_service.send_message(user.user_id, message)
        
        # For daily planners experiencing negative sentiment, offer one task or rest
        offer_simplified_options(user)
    else:
        # Keep or switch to weekly planning
        user.update_planning_type('weekly')
        logger.info(f"User {user.user_id} classified as weekly planner with sentiment score: {sentiment_score}")
        
        # Send confirmation message
        message = "Thank you for sharing how you're feeling about the week ahead. 💫 I'll be here each morning to offer a gentle check-in, if that feels helpful for your journey."
        whatsapp_service.send_message(user.user_id, message)
        
        # Prompt for weekly tasks
        prompt_for_weekly_tasks(user)

def offer_simplified_options(user):
    """
    Offer simplified task options to a user who's feeling overwhelmed
    
    Args:
        user (User): The user to prompt
    """
    whatsapp_service = get_whatsapp_service(user.account_index)
    
    response = "Let's embrace whatever feels nurturing for you today. Would you prefer:"
    
    # Send interactive message with buttons
    buttons = [
        {"id": "one_task", "title": "One tiny step"},
        {"id": "rest_today", "title": "Rest & recharge"}
    ]
    
    whatsapp_service.send_interactive_buttons(user.user_id, response, buttons)
    logger.info(f"Offered simplified options to {user.user_id}")

def prompt_for_weekly_tasks(user):
    """
    Prompt a user to set tasks for the week
    
    Args:
        user (User): The user to prompt
    """
    whatsapp_service = get_whatsapp_service(user.account_index)
    
    response = "If it feels helpful, you could share some intentions for your week. No need to plan everything - even 1-3 gentle focuses can provide a soft framework. What might feel nurturing to focus on this week?"
    whatsapp_service.send_message(user.user_id, response)
    
    logger.info(f"Prompted for weekly tasks for user {user.user_id}")

def parse_weekly_tasks(user, message_text):
    """
    Parse weekly tasks from a user message and create task entries
    
    Args:
        user (User): The user who sent the message
        message_text (str): The message text containing tasks by day
    """
    whatsapp_service = get_whatsapp_service(user.account_index)
    
    # Days of the week patterns
    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    
    # Map to store tasks by day
    tasks_by_day = {}
    
    # Initialize with empty lists for each day
    for day in days:
        tasks_by_day[day] = []
    
    # Split the message by lines
    lines = message_text.lower().split('\n')
    
    # Current day being processed
    current_day = None
    
    # Process each line
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Check if this line starts with a day of the week
        for day in days:
            if line.startswith(day):
                current_day = day
                # Extract tasks part (after the "day:" part)
                tasks_part = re.sub(r'^' + day + r'[:\s]*', '', line, flags=re.IGNORECASE)
                # Process tasks for this day
                if tasks_part:
                    process_tasks_for_day(tasks_by_day, current_day, tasks_part)
                break
        else:
            # If no day prefix and we have a current day, add to that day
            if current_day and line:
                process_tasks_for_day(tasks_by_day, current_day, line)
    
    # Create task objects for each day with proper scheduling
    task_count = 0
    today = datetime.now()
    
    for i, day in enumerate(days):
        # Calculate the date for this day
        # Finding the next occurrence of this day
        day_index = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, 
                     "friday": 4, "saturday": 5, "sunday": 6}[day]
        
        # Calculate days to add to get to the next occurrence of this day
        days_ahead = (day_index - today.weekday()) % 7
        if days_ahead == 0 and today.hour >= 17:  # If it's already past 5pm, use next week
            days_ahead = 7
        
        task_date = today + timedelta(days=days_ahead)
        
        # Create tasks for this day
        for task_description in tasks_by_day[day]:
            Task.create(user.user_id, task_description, scheduled_date=task_date)
            task_count += 1
    
    # Send confirmation message
    if task_count > 0:
        message = f"Thank you for sharing your intentions for the week 💫 I've gently noted your {task_count} focus areas. Remember, these are flexible guides, not rigid expectations - we can always adjust as needed."
        whatsapp_service.send_message(user.user_id, message)
    else:
        message = "I didn't quite catch your intentions for the week. No pressure at all - when you're ready, you could share them in a format like: 'Monday: gentle stretching, call friend' or just list what feels manageable without specific days."
        whatsapp_service.send_message(user.user_id, message)

def process_tasks_for_day(tasks_by_day, day, tasks_text):
    """
    Process tasks for a specific day
    
    Args:
        tasks_by_day (dict): Dictionary mapping days to task lists
        day (str): The day to add tasks for
        tasks_text (str): Text containing the tasks
    """
    # Split by commas and semicolons
    tasks = tasks_text.replace(';', ',').split(',')
    
    # Add non-empty tasks
    for task in tasks:
        task = task.strip()
        if task:
            tasks_by_day[day].append(task) 