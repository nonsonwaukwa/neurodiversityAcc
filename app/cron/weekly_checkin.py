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
        message = "I understand you're feeling a bit overwhelmed. I'll help you take it day by day with more frequent check-ins and simpler planning."
        whatsapp_service.send_message(user.user_id, message)
        
        # For daily planners experiencing negative sentiment, offer one task or rest
        offer_simplified_options(user)
    else:
        # Keep or switch to weekly planning
        user.update_planning_type('weekly')
        logger.info(f"User {user.user_id} classified as weekly planner with sentiment score: {sentiment_score}")
        
        # Send confirmation message
        message = "Sounds like you're ready to plan for the week! I'll check in each morning to help you with your daily tasks."
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
    
    response = "Let's make today manageable. Would you prefer to:"
    
    # Send interactive message with buttons
    buttons = [
        {"id": "one_task", "title": "One small task"},
        {"id": "rest_today", "title": "Rest today"}
    ]
    
    whatsapp_service.send_interactive_buttons(user.user_id, response, buttons)
    logger.info(f"Offered simplified options to {user.user_id}")

def prompt_for_weekly_tasks(user):
    """
    Prompt the user for tasks for the entire week
    
    Args:
        user (User): The user to prompt
    """
    whatsapp_service = get_whatsapp_service(user.account_index)
    
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
        message = f"Great! I've added {task_count} tasks for your week. I'll remind you about each day's tasks in our daily check-ins."
        whatsapp_service.send_message(user.user_id, message)
    else:
        message = "I didn't catch any tasks. Please try again with the format:\nMonday: Task 1, Task 2\nTuesday: Task 3"
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