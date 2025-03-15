from app.models.user import User
from app.models.task import Task
from app.models.checkin import CheckIn
from app.services.whatsapp import get_whatsapp_service
from app.services.tasks import get_task_service, send_task_buttons
from app.services.analytics import get_analytics_service
import logging
from datetime import datetime

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
                
                # Store this message as a check-in
                CheckIn.create(user.user_id, checkin_message, CheckIn.TYPE_DAILY)
                
                if response:
                    logger.info(f"Successfully sent daily check-in to user {user.user_id}")
                else:
                    logger.error(f"Failed to send daily check-in to user {user.user_id}")
            
            except Exception as e:
                logger.error(f"Error sending daily check-in to user {user.user_id}: {e}")

def process_daily_response(user, message_text, sentiment_score):
    """
    Process a response to a daily check-in
    
    Args:
        user (User): The user who responded
        message_text (str): The text of the message
        sentiment_score (float): The sentiment score of the message
    """
    whatsapp_service = get_whatsapp_service(user.account_index)
    analytics_service = get_analytics_service()
    
    # Get previous sentiment for comparison
    previous_sentiment = _get_previous_sentiment(user.user_id)
    
    # Log sentiment change if significant
    if previous_sentiment is not None:
        analytics_service.log_mood_change(
            user.user_id, 
            previous_sentiment, 
            sentiment_score, 
            context="daily-checkin"
        )
    
    # Get sentiment trend to personalize response
    sentiment_trend = analytics_service.get_sentiment_trend(user.user_id)
    
    # If sentiment is negative, give them easy options
    if sentiment_score < -0.3:
        # For negative sentiment, offer less demanding options
        
        # Acknowledge mood change if significant
        acknowledgment = _get_mood_acknowledgment(previous_sentiment, sentiment_score, sentiment_trend)
        
        if user.planning_type == 'weekly':
            # For weekly planners with negative sentiment,
            # offer a choice of one task from their pre-set tasks or rest
            today = datetime.now()
            tasks = Task.get_for_user(user.user_id, scheduled_date=today)
            
            if tasks:
                # They have tasks scheduled for today
                response = f"{acknowledgment} Would you prefer to:"
                
                buttons = [
                    {"id": "choose_one_task", "title": "Choose one task"},
                    {"id": "one_task", "title": "New small task"},
                    {"id": "rest_today", "title": "Rest today"}
                ]
                
                whatsapp_service.send_interactive_buttons(user.user_id, response, buttons)
            else:
                # No tasks scheduled for today, offer standard options
                offer_simplified_options(user, acknowledgment)
        else:
            # For daily planners with negative sentiment, offer simplified options
            offer_simplified_options(user, acknowledgment)
    else:
        # For neutral or positive sentiment
        
        # Create acknowledgment for positive/neutral mood
        acknowledgment = _get_mood_acknowledgment(previous_sentiment, sentiment_score, sentiment_trend)
        
        if user.planning_type == 'weekly':
            # For weekly planners, show their pre-set tasks for today
            show_todays_tasks(user, acknowledgment)
        else:
            # For daily planners, ask for up to 3 tasks
            response = f"{acknowledgment} What tasks would you like to focus on today? You can list up to 3 tasks, and I'll help you track them."
            whatsapp_service.send_message(user.user_id, response)
    
    logger.info(f"Processed daily check-in response from {user.user_id}")

def _get_previous_sentiment(user_id):
    """
    Get the user's previous sentiment score
    
    Args:
        user_id (str): The user's ID
        
    Returns:
        float or None: The previous sentiment score, or None if no previous check-ins
    """
    # Get user's previous check-ins that were responses (not system messages)
    previous_checkins = CheckIn.get_for_user(
        user_id, 
        limit=2,  # Get 2 to skip the current one
        is_response=True
    )
    
    # Skip the current check-in (should be first in list)
    if len(previous_checkins) > 1:
        return previous_checkins[1].sentiment_score
    
    return None

def _get_mood_acknowledgment(previous_sentiment, current_sentiment, sentiment_trend):
    """
    Generate a personalized acknowledgment based on mood change
    
    Args:
        previous_sentiment (float): Previous sentiment score
        current_sentiment (float): Current sentiment score
        sentiment_trend (dict): Sentiment trend information
        
    Returns:
        str: Personalized acknowledgment
    """
    # Default acknowledgments based on current sentiment
    if current_sentiment < -0.3:
        acknowledgment = "I understand you're not feeling your best today."
    elif current_sentiment > 0.3:
        acknowledgment = "Great to hear you're feeling positive today!"
    else:
        acknowledgment = "Thanks for checking in today."
    
    # If we have a previous sentiment, acknowledge changes
    if previous_sentiment is not None:
        change = current_sentiment - previous_sentiment
        
        # Significant improvement
        if change > 0.3:
            acknowledgment = "I'm glad to see your mood has improved since last time!"
        # Significant decline
        elif change < -0.3:
            acknowledgment = "I notice you're feeling a bit lower than before. That's completely okay."
    
    # Add trend-based encouragement
    if sentiment_trend and sentiment_trend["trend"] == "improving":
        acknowledgment += " You've been making positive progress lately."
    elif sentiment_trend and sentiment_trend["trend"] == "declining" and current_sentiment > -0.3:
        acknowledgment += " Remember that ups and downs are normal and all part of the journey."
    
    return acknowledgment

def offer_simplified_options(user, acknowledgment=None):
    """
    Offer simplified task options to a user who's feeling overwhelmed
    
    Args:
        user (User): The user to prompt
        acknowledgment (str, optional): Personalized acknowledgment to include
    """
    whatsapp_service = get_whatsapp_service(user.account_index)
    
    response = acknowledgment if acknowledgment else "Let's make today manageable."
    response += " Would you prefer to:"
    
    # Send interactive message with buttons
    buttons = [
        {"id": "one_task", "title": "One small task"},
        {"id": "rest_today", "title": "Rest today"}
    ]
    
    whatsapp_service.send_interactive_buttons(user.user_id, response, buttons)
    logger.info(f"Offered simplified options to {user.user_id}")

def handle_one_task_request(user):
    """
    Handle a request to focus on one task
    
    Args:
        user (User): The user who made the request
    """
    whatsapp_service = get_whatsapp_service(user.account_index)
    
    response = "What's one small thing you'd like to accomplish today?"
    whatsapp_service.send_message(user.user_id, response)
    
    logger.info(f"Sent one task request to {user.user_id}")

def handle_choose_one_task(user):
    """
    Handle a request to choose one task from pre-set tasks
    
    Args:
        user (User): The user who made the request
    """
    whatsapp_service = get_whatsapp_service(user.account_index)
    
    # Get today's tasks
    today = datetime.now()
    tasks = Task.get_for_user(user.user_id, scheduled_date=today)
    
    if tasks:
        response = "Here are your tasks for today. Which one would you like to focus on?"
        
        # Create task selection buttons
        buttons = []
        for task in tasks[:3]:  # Limit to 3 options
            task_id = task.task_id
            short_desc = task.description[:20] + "..." if len(task.description) > 20 else task.description
            buttons.append({
                "id": f"select_task_{task_id}",
                "title": short_desc
            })
        
        whatsapp_service.send_interactive_buttons(user.user_id, response, buttons)
    else:
        # Fallback if no tasks are found
        handle_one_task_request(user)
    
    logger.info(f"Sent task selection options to {user.user_id}")

def handle_task_selection(user, task_id):
    """
    Handle selection of a specific task to focus on
    
    Args:
        user (User): The user who made the selection
        task_id (str): The ID of the selected task
    """
    whatsapp_service = get_whatsapp_service(user.account_index)
    
    # Get the selected task
    task = Task.get(task_id)
    
    if task:
        # Mark other tasks as not for today (can be implemented by setting a 'focus' flag)
        # This is a placeholder for that functionality
        
        message = f"Great! Today you'll focus on: {task.description}\n\nI'll check in later to see how it's going."
        whatsapp_service.send_message(user.user_id, message)
        
        # Send buttons for this task
        send_task_buttons(user, task)
    else:
        # Fallback if task not found
        handle_one_task_request(user)

def handle_rest_request(user):
    """
    Handle a request to rest for the day
    
    Args:
        user (User): The user who made the request
    """
    whatsapp_service = get_whatsapp_service(user.account_index)
    task_service = get_task_service()
    
    # Get a self-care tip
    self_care_tip = task_service.get_self_care_tip()
    
    response = f"Taking a rest day is completely okay. Remember to be kind to yourself. Here's a self-care tip: {self_care_tip}\n\nI'll check in with you tomorrow!"
    whatsapp_service.send_message(user.user_id, response)
    
    logger.info(f"Processed rest request for {user.user_id}")

def show_todays_tasks(user, acknowledgment=None):
    """
    Show the user their tasks scheduled for today
    
    Args:
        user (User): The user to show tasks to
        acknowledgment (str, optional): Personalized acknowledgment to include
    """
    whatsapp_service = get_whatsapp_service(user.account_index)
    
    # Get today's date
    today = datetime.now()
    
    # Get tasks scheduled for today
    tasks = Task.get_for_user(user.user_id, scheduled_date=today)
    
    prefix = acknowledgment if acknowledgment else ""
    
    if tasks:
        # Format task list
        task_list = "\n".join([f"- {task.description}" for task in tasks])
        
        message = f"{prefix} Here are your tasks for today:\n{task_list}\n\nWould you like to get started on these?"
        whatsapp_service.send_message(user.user_id, message)
        
        # Send buttons for each task
        for task in tasks:
            send_task_buttons(user, task)
    else:
        # No tasks scheduled
        message = f"{prefix} You don't have any tasks scheduled for today. Would you like to add some?"
        whatsapp_service.send_message(user.user_id, message)
    
    logger.info(f"Showed today's tasks to {user.user_id}")

def send_daily_reminders():
    """
    Send reminders to users about their uncompleted tasks
    """
    # Get all active users
    users = User.get_all_active()
    
    for user in users:
        _send_user_task_reminder(user)

def _send_user_task_reminder(user):
    """
    Send a task reminder to a specific user
    
    Args:
        user (User): The user to send the reminder to
    """
    whatsapp_service = get_whatsapp_service(user.account_index)
    task_service = get_task_service()
    
    # Get uncompleted tasks for the user
    # For weekly planners, only include today's scheduled tasks
    today = None
    if user.planning_type == 'weekly':
        today = datetime.now()
    
    # Get tasks by status
    pending_tasks = Task.get_for_user(user.user_id, status=Task.STATUS_PENDING, scheduled_date=today)
    in_progress_tasks = Task.get_for_user(user.user_id, status=Task.STATUS_IN_PROGRESS, scheduled_date=today)
    stuck_tasks = Task.get_for_user(user.user_id, status=Task.STATUS_STUCK, scheduled_date=today)
    
    active_tasks = pending_tasks + in_progress_tasks + stuck_tasks
    
    if not active_tasks:
        # No need to send a reminder if there are no active tasks
        return
    
    # Create a reminder message
    if len(active_tasks) == 1:
        task = active_tasks[0]
        message = f"Just checking in on your task: {task.description}\n\nHow's it going?"
        
        # Send buttons for this task
        send_task_buttons(user, task)
    else:
        # Multiple tasks
        message = "Just checking in on your tasks for today:\n"
        
        for task in active_tasks:
            status_str = ""
            if task.status == Task.STATUS_IN_PROGRESS:
                status_str = " (in progress)"
            elif task.status == Task.STATUS_STUCK:
                status_str = " (stuck)"
                
            message += f"- {task.description}{status_str}\n"
        
        message += "\nLet me know how they're going!"
        whatsapp_service.send_message(user.user_id, message)
        
        # Send buttons for each task
        for task in active_tasks:
            send_task_buttons(user, task)
    
    logger.info(f"Sent task reminder to {user.user_id} for {len(active_tasks)} tasks") 