from app.models.user import User
from app.models.task import Task
from app.models.checkin import CheckIn
from app.services.whatsapp import get_whatsapp_service
from app.services.analytics import get_analytics_service
from app.services.enhanced_analytics import EnhancedAnalyticsService
from app.services.conversation_analytics import ConversationAnalyticsService
from app.services.tasks import get_task_service
import logging
from datetime import datetime

# Set up logger
logger = logging.getLogger(__name__)

def send_end_of_day_checkin():
    """Send personalized end of day check-in messages to all users"""
    logger.info("Running end of day check-in cron job")
    
    # Get all users
    users = User.get_all()
    
    if not users:
        logger.info("No users found for end of day check-in")
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
                # Get user's activity for the day
                tasks = Task.get_for_user(user.user_id, scheduled_date=datetime.now())
                has_checked_in = CheckIn.has_checked_in_today(user.user_id)
                completed_tasks = [t for t in tasks if t.status == 'done']
                incomplete_tasks = [t for t in tasks if t.status != 'done']
                
                # Format the message with the user's name
                name = user.name.split('_')[0] if '_' in user.name else user.name
                
                # Generate personalized message based on day's activity
                if not has_checked_in and not tasks:
                    message = (
                        f"Hi {name} 💫 How was your day? Feel free to share in any way that feels "
                        "comfortable - a voice note, message, or even just a quick emoji. No pressure, "
                        "just here to listen 🌙"
                    )
                elif tasks and completed_tasks and not incomplete_tasks:
                    message = (
                        f"Hi {name} 💫 Amazing work today! You completed all your tasks - "
                        "that's fantastic! Would you like to share how your day went? You can send "
                        "a voice note or message, whatever feels most natural 🌙"
                    )
                elif tasks and completed_tasks and incomplete_tasks:
                    task_list = "\n".join([f"• {task.description}" for task in incomplete_tasks])
                    message = (
                        f"Hi {name} 💫 I see you completed {len(completed_tasks)} tasks today - "
                        "that's wonderful! You still have some tasks that weren't marked as done:\n\n"
                        f"{task_list}\n\n"
                        "Would you like to update their status or share how your day went? "
                        "You can mark them as done, in progress, or stuck, or just share your thoughts 🌙"
                    )
                elif tasks and not completed_tasks:
                    task_list = "\n".join([f"• {task.description}" for task in tasks])
                    message = (
                        f"Hi {name} 💫 How did your day go? I notice you have some tasks that weren't marked as done:\n\n"
                        f"{task_list}\n\n"
                        "Some days are for doing, others for being - both are equally valid. "
                        "Would you like to update their status or just share your thoughts? "
                        "You can mark them as done, in progress, or stuck 🌙"
                    )
                
                logger.info(f"Sending end of day check-in to user {user.user_id} (account {account_index})")
                response = whatsapp_service.send_message(user.user_id, message)
                
                # Store this message as a check-in
                CheckIn.create(user.user_id, message, CheckIn.TYPE_END_OF_DAY)
                
                if response:
                    logger.info(f"Successfully sent end of day check-in to user {user.user_id}")
                else:
                    logger.error(f"Failed to send end of day check-in to user {user.user_id}")
            
            except Exception as e:
                logger.error(f"Error sending end of day check-in to user {user.user_id}: {e}")

def process_end_of_day_response(user, message_text, sentiment_score):
    """
    Process a response to an end of day check-in
    
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
    conversation_analytics.log_conversation_themes(user.user_id, message_text, 'end_of_day')
    
    # Get previous sentiment for comparison
    previous_sentiment = _get_previous_sentiment(user.user_id)
    
    # Log sentiment change if significant
    if previous_sentiment is not None:
        analytics_service.log_mood_change(
            user.user_id, 
            previous_sentiment, 
            sentiment_score, 
            context="end-of-day-checkin"
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
            f"I hear you, and it sounds like today had its challenges. That's completely okay "
            f"and normal. 💜{streak_message}\nWould you like some gentle support as you wind down?"
        )
        send_support_options(user, message)
    else:
        # For neutral or positive sentiment
        acknowledgment = _get_mood_acknowledgment(previous_sentiment, sentiment_score, sentiment_trend)
        message = f"{acknowledgment}{streak_message}\nRest well, and we'll connect again tomorrow 🌙"
        whatsapp_service.send_message(user.user_id, message)
    
    logger.info(f"Processed end of day check-in response from {user.user_id}")

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
        acknowledgment = "I hear that today had its challenges, and that's completely valid. 💜 Your feelings matter."
    elif current_sentiment > 0.3:
        acknowledgment = "It's lovely to sense your positive energy! ✨ Those good moments are worth cherishing."
    else:
        acknowledgment = "Thank you for sharing how your day went. 💫 It's always nice to connect with you."
    
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

def send_support_options(user, message=None):
    """
    Send support options to a user who might need extra care
    
    Args:
        user (User): The user to send options to
        message (str, optional): Custom message to include
    """
    whatsapp_service = get_whatsapp_service(user.account_index)
    
    response = message if message else "Let's embrace whatever feels nurturing for you right now."
    response += " Would any of these feel supportive?"
    
    # Send interactive message with buttons
    buttons = [
        {"id": "adhd_strategies", "title": "ADHD-friendly strategies"},
        {"id": "self_care", "title": "Self-care tips"},
        {"id": "gentle_reminder", "title": "Just a gentle reminder"}
    ]
    
    whatsapp_service.send_interactive_buttons(user.user_id, response, buttons)
    logger.info(f"Sent support options to {user.user_id}") 