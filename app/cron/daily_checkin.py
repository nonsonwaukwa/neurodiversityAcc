from app.models.user import User
from app.models.task import Task
from app.models.checkin import CheckIn
from app.services.whatsapp import get_whatsapp_service
from app.services.tasks import get_task_service, send_task_buttons
from app.services.analytics import get_analytics_service
from app.services.enhanced_analytics import EnhancedAnalyticsService
from app.services.conversation_analytics import ConversationAnalyticsService
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
                checkin_message = f"Good morning {name} 💫 I hope you've been able to rest. How are you feeling today? Whatever you're experiencing is completely valid."
                
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
    enhanced_analytics = EnhancedAnalyticsService()
    conversation_analytics = ConversationAnalyticsService()
    
    # Log conversation themes
    conversation_analytics.log_conversation_themes(user.user_id, message_text, 'checkin')
    
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
    
    # Update user's streak
    streak_count, streak_maintained = enhanced_analytics.update_user_streak(user.user_id)
    
    # Get the original check-in message to calculate response time
    recent_checkins = CheckIn.get_for_user(
        user.user_id,
        limit=1,
        is_response=False
    )
    
    if recent_checkins:
        original_checkin = recent_checkins[0]
        enhanced_analytics.log_response_time(
            user.user_id,
            original_checkin.created_at,
            datetime.now()
        )
    
    # Get sentiment trend to personalize response
    sentiment_trend = analytics_service.get_sentiment_trend(user.user_id)
    
    # Track engagement
    engagement_metrics = enhanced_analytics.track_user_engagement(user.user_id)
    
    # Customize response based on streak
    streak_message = ""
    if streak_maintained and streak_count > 1:
        streak_message = f"\n🔥 Amazing! You've maintained a {streak_count}-day streak!"
    
    if sentiment_score < -0.3:  # Overwhelmed/negative sentiment
        # Offer support and simplified options
        message = (
            f"I hear you, and it sounds like today might be feeling a bit heavy. That's completely okay and normal. 💜{streak_message}\n"
            "Would you like to take a gentle approach today? Perhaps:"
        )
        send_support_options(user, message)
    else:
        # For neutral or positive sentiment
        acknowledgment = _get_mood_acknowledgment(previous_sentiment, sentiment_score, sentiment_trend)
        
        if user.planning_type == 'weekly':
            # For weekly planners, show their pre-set tasks for today
            show_todays_tasks(user, f"{acknowledgment}{streak_message}")
        else:
            # For daily planners, ask for up to 3 tasks
            response = f"{acknowledgment}{streak_message}\nIf you'd like, you could share what you might focus on today. No pressure - you could list 1-3 things that feel manageable, or we can just check in."
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
        acknowledgment = "I hear that today might be feeling a bit challenging for you, and that's completely valid. 💜 Your feelings matter."
    elif current_sentiment > 0.3:
        acknowledgment = "It's lovely to sense your positive energy today! ✨ Those good moments are worth cherishing."
    else:
        acknowledgment = "Thank you for sharing how you're feeling today. 💫 It's always nice to connect with you."
    
    # If we have a previous sentiment, acknowledge changes
    if previous_sentiment is not None:
        change = current_sentiment - previous_sentiment
        
        # Significant improvement
        if change > 0.3:
            acknowledgment = "I notice there seems to be a little more brightness in your message today compared to before, which is lovely to see. 🌱"
        # Significant decline
        elif change < -0.3:
            acknowledgment = "It sounds like things might be feeling a bit heavier than before, and that's completely okay. 💗 All feelings are welcome here."
    
    # Add trend-based encouragement
    if sentiment_trend and sentiment_trend["trend"] == "improving":
        acknowledgment += " I've noticed a gentle positive shift in our recent conversations, which is beautiful to witness."
    elif sentiment_trend and sentiment_trend["trend"] == "declining" and current_sentiment > -0.3:
        acknowledgment += " Remember that all emotional waves are natural and valid - the ebbs and flows are part of being human."
    
    return acknowledgment

def offer_simplified_options(user, acknowledgment=None):
    """
    Offer simplified task options to a user who's feeling overwhelmed
    
    Args:
        user (User): The user to prompt
        acknowledgment (str, optional): Personalized acknowledgment to include
    """
    whatsapp_service = get_whatsapp_service(user.account_index)
    
    response = acknowledgment if acknowledgment else "Let's embrace whatever feels nurturing for you today."
    response += " Would any of these feel supportive?"
    
    # Send interactive message with buttons
    buttons = [
        {"id": "tiny_step", "title": "One tiny, gentle step"},
        {"id": "rest_and_recharge", "title": "Rest & recharge today"}
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
    
    response = "Is there one tiny, gentle thing that might feel nurturing to focus on today? No pressure at all - even the smallest intention counts. 💫"
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
        response = "Here are your intentions for today. Would you like to gently focus on one of these? Remember, there's no pressure - just an invitation to explore what feels most manageable:"
        
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
        
        message = f"Thank you for sharing what feels right for you today 💫 You've chosen to explore: {task.description}\n\nI'll be here to gently check in later, if that's helpful."
        whatsapp_service.send_message(user.user_id, message)
        
        # Send buttons for this task
        send_task_buttons(user, task)
    else:
        # Fallback if task not found
        handle_one_task_request(user)
    
    logger.info(f"User {user.user_id} selected task {task_id}")

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
    
    response = f"Taking a rest day is not just okay - it's a wise and necessary form of self-care. 💖 Your body and mind deserve that kindness. If it feels right, here's a gentle self-care suggestion: {self_care_tip}\n\nI'll be here tomorrow with the same unconditional support."
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
        
        message = f"{prefix} Here are the gentle intentions you set for today:\n{task_list}\n\nWould you like to explore any of these when you feel ready? Remember, there's no pressure - these are just guides, not obligations. 💫"
        whatsapp_service.send_message(user.user_id, message)
        
        # Send buttons for each task
        for task in tasks:
            send_task_buttons(user, task)
    else:
        # No tasks scheduled
        message = f"{prefix} You don't have any specific intentions set for today, which is completely okay. Would you like to add something small that might feel nurturing or helpful?"
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
        message = f"Just a gentle check-in about: {task.description}\n\nHow are things going with this? Remember, progress looks different for everyone, and even tiny steps count. 💫"
        
        # Send buttons for this task
        send_task_buttons(user, task)
    else:
        # Multiple tasks
        message = "I'm offering a soft check-in on the intentions you set:\n"
        
        for task in active_tasks:
            status_str = ""
            if task.status == Task.STATUS_IN_PROGRESS:
                status_str = " (in progress)"
            elif task.status == Task.STATUS_STUCK:
                status_str = " (feeling challenging)"
                
            message += f"- {task.description}{status_str}\n"
        
        message += "\nHow are things feeling? There's no expectation - I'm just here to support however is helpful for you. 💖"
        whatsapp_service.send_message(user.user_id, message)
        
        # Send buttons for each task
        for task in active_tasks:
            send_task_buttons(user, task)
    
    logger.info(f"Sent task reminder to {user.user_id} for {len(active_tasks)} tasks")

def handle_task_creation(user, task_description):
    """
    Handle creation of a new task
    
    Args:
        user (User): The user creating the task
        task_description (str): The task description
    """
    task_service = get_task_service()
    conversation_analytics = ConversationAnalyticsService()
    
    # Log task themes
    conversation_analytics.log_conversation_themes(user.user_id, task_description, 'task')
    
    # Create the task
    task = task_service.create_task(user.user_id, task_description)
    
    # Send task buttons
    send_task_buttons(user, task)
    
    logger.info(f"Created task for {user.user_id}: {task_description}") 