import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models.user import User
from app.models.task import Task
from app.models.checkin import CheckIn
from app.services.whatsapp import get_whatsapp_service, WhatsAppService
from app.services.analytics import get_analytics_service
from app.services.enhanced_analytics import EnhancedAnalyticsService
from app.services.conversation_analytics import ConversationAnalyticsService
from app.services.tasks import get_task_service
import logging
from datetime import datetime, timedelta, timezone
from flask import current_app

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

def send_end_of_day_checkins():
    """Send end of day check-ins to all active users."""
    logger.info("Running end of day check-in cron job")
    
    try:
        # Log environment variables for debugging
        logger.info("Checking environment configuration:")
        logger.info(f"FLASK_ENV: {os.environ.get('FLASK_ENV')}")
        logger.info(f"FLASK_DEBUG: {os.environ.get('FLASK_DEBUG')}")
        logger.info(f"WHATSAPP_API_URL: {os.environ.get('WHATSAPP_API_URL')}")
        logger.info(f"WHATSAPP_PHONE_NUMBER_ID set: {'Yes' if os.environ.get('WHATSAPP_PHONE_NUMBER_ID') else 'No'}")
        logger.info(f"WHATSAPP_ACCESS_TOKEN set: {'Yes' if os.environ.get('WHATSAPP_ACCESS_TOKEN') else 'No'}")
        
        # Log Flask app configuration
        logger.info("Checking Flask app configuration:")
        logger.info(f"WHATSAPP_API_URL from config: {current_app.config.get('WHATSAPP_API_URL')}")
        logger.info(f"WHATSAPP_PHONE_NUMBER_IDS from config: {current_app.config.get('WHATSAPP_PHONE_NUMBER_IDS')}")
        logger.info(f"WHATSAPP_ACCESS_TOKENS from config: {current_app.config.get('WHATSAPP_ACCESS_TOKENS')}")
        
        # Verify WhatsApp configuration first
        logger.info("Initializing WhatsApp service for testing...")
        whatsapp_service = get_whatsapp_service(0)  # Test with default account
        
        # Test connection and log detailed response
        logger.info("Testing WhatsApp API connection...")
        connection_result = whatsapp_service.check_connection()
        if not connection_result:
            logger.error("WhatsApp configuration test failed. Please check your credentials.")
            # Get account info for more details
            account_info = whatsapp_service.get_account_info()
            if account_info:
                logger.error(f"Account info: {account_info}")
            return
        
        logger.info("WhatsApp configuration test passed successfully")
        
        # Get all active users
        users = User.get_all_active()
        logger.debug(f"Found {len(users) if users else 0} active users")
        
        if not users:
            logger.info("No active users found for end of day check-ins")
            return
        
        # Group users by account
        users_by_account = {}
        for user in users:
            account_index = user.account_index
            if account_index not in users_by_account:
                users_by_account[account_index] = []
            users_by_account[account_index].append(user)
        
        logger.debug(f"Grouped users into {len(users_by_account)} accounts")
        
        # Process each account
        for account_index, account_users in users_by_account.items():
            # Get the WhatsApp service for this account
            whatsapp_service = get_whatsapp_service(account_index)
            logger.debug(f"Processing {len(account_users)} users for account {account_index}")
            
            # Process each user in this account
            for user in account_users:
                try:
                    _send_end_of_day_checkin(user.user_id, whatsapp_service)
                except Exception as e:
                    logger.error(f"Error sending end of day check-in to user {user.user_id}: {e}", exc_info=True)
                    
    except Exception as e:
        logger.error(f"Unexpected error in end of day check-ins: {e}", exc_info=True)

def _send_end_of_day_checkin(user_id: str, whatsapp_service: WhatsAppService) -> bool:
    """Send end of day check-in to a user."""
    logger.info(f"Sending end of day check-in to user {user_id}")

    # Check if we've already sent an end-of-day message today
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_messages = CheckIn.get_for_user(user_id, start_date=today)
    
    # Check if any of today's messages are end-of-day messages
    for message in today_messages:
        if message.response and "As we wrap up the day" in message.response:
            logger.info(f"Already sent end-of-day message to user {user_id} today")
            return True

    # Get user check-ins for today (excluding system messages)
    user_checkins = [c for c in today_messages if c.response and 
                    "As we wrap up the day" not in c.response and
                    "Would you like to:" not in c.response and
                    "Just reply with what feels right for you" not in c.response]
    
    logger.debug(f"Found {len(user_checkins)} user check-ins today for user {user_id}")
    
    # Get analytics about the user's day
    analytics_service = get_analytics_service()
    task_service = get_task_service()
    
    # Get completed tasks for today
    completed_tasks = Task.get_completed_for_user(
        user_id=user_id,
        start_date=today
    )
    
    logger.debug(f"Found {len(completed_tasks) if completed_tasks else 0} completed tasks today for user {user_id}")
    
    # Get sentiment analysis
    sentiment_trend = analytics_service.get_sentiment_trend(user_id)
    logger.debug(f"Got sentiment trend for user {user_id}: {sentiment_trend}")
    
    # Get self-care tip
    self_care_tip = task_service.get_self_care_tip()
    
    # Compose the message
    message = f"Hi {user_id}! 🌙 As we wrap up the day, let's take a gentle moment to reflect.\n\n"
    
    if user_checkins:
        message += f"Today you shared {len(user_checkins)} check-ins with me 💭\n"
    
    if completed_tasks:
        message += f"And completed {len(completed_tasks)} tasks ✅\n"
    
    if sentiment_trend:
        message += f"\nYour emotional journey today: {sentiment_trend}\n"
    
    message += (
        f"\nRemember: {self_care_tip}\n\n"
        f"Would you like to:\n"
        f"1. Reflect on today\n"
        f"2. Plan for tomorrow\n"
        f"3. Share your thoughts\n\n"
        f"Just reply with what feels right for you 🌙"
    )
    
    try:
        # Send message directly like daily check-in does
        response = whatsapp_service.send_message(user_id, message)
        if response:
            logger.info(f"Successfully sent end of day check-in to user {user_id}")
            # Store this message as a check-in
            CheckIn.create(user_id, message, CheckIn.TYPE_END_OF_DAY)
        else:
            logger.error(f"Failed to send end of day check-in to user {user_id}: No response from WhatsApp API")
    except Exception as e:
        logger.error(f"Failed to send end of day check-in to user {user_id}: {str(e)}")
        raise

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
    
    header = "Need Some Support? 💜"
    body = message if message else "Let's embrace whatever feels nurturing for you right now."
    button_text = "View Support Options"
    
    sections = [{
        "title": "Available Support",
        "rows": [
            {
                "id": "adhd_strategies",
                "title": "ADHD-friendly strategies",
                "description": "Quick tips to help manage focus and tasks"
            },
            {
                "id": "self_care",
                "title": "Self-care tips",
                "description": "Gentle reminders for taking care of yourself"
            },
            {
                "id": "gentle_reminder",
                "title": "A gentle reminder",
                "description": "Sometimes we just need a kind word"
            },
            {
                "id": "breathing_exercise",
                "title": "Quick breathing exercise",
                "description": "A simple way to find calm in the moment"
            },
            {
                "id": "positive_affirmation",
                "title": "Positive affirmation",
                "description": "Words of encouragement just for you"
            }
        ]
    }]
    
    success = whatsapp_service.send_list_message_with_fallback(
        to=user.user_id,
        header_text=header,
        body_text=body,
        button_text=button_text,
        sections=sections
    )
    
    if success:
        logger.info(f"Sent support options to {user.user_id}")
    else:
        logger.error(f"Failed to send support options to {user.user_id}")

if __name__ == "__main__":
    send_end_of_day_checkins() 