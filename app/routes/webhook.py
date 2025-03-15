from flask import Blueprint, request, jsonify
from app.services.whatsapp import get_whatsapp_service, get_whatsapp_service_for_number
from app.services.sentiment import get_sentiment_service
from app.services.tasks import get_task_service, send_task_buttons
from app.services.validation import ResponseValidator
from app.services.voice import VoiceTranscriptionService
from app.models.user import User
from app.models.checkin import CheckIn
from app.models.task import Task
from app.cron.daily_checkin import process_daily_response, handle_one_task_request, handle_rest_request, handle_choose_one_task, handle_task_selection
from app.cron.weekly_checkin import process_weekly_response
from app.cron.weekly_report import process_win_reflection
import json
import logging
from datetime import datetime, timedelta

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create blueprint
webhook_bp = Blueprint('webhook', __name__)

# Initialize services
validator = ResponseValidator()
voice_service = VoiceTranscriptionService()

# Store processed message IDs with timestamps
processed_messages = {}

def is_message_processed(message_id):
    """
    Check if a message has already been processed and clean up old entries
    
    Args:
        message_id (str): The WhatsApp message ID
        
    Returns:
        bool: True if message was already processed, False otherwise
    """
    current_time = datetime.now()
    
    # Clean up messages older than 1 hour
    expired = [mid for mid, timestamp in processed_messages.items() 
              if current_time - timestamp > timedelta(hours=1)]
    for mid in expired:
        processed_messages.pop(mid)
    
    # Check if message was processed
    if message_id in processed_messages:
        return True
    
    # Mark message as processed
    processed_messages[message_id] = current_time
    return False

@webhook_bp.route('/webhook', methods=['GET', 'POST'])
def webhook():
    """Handle WhatsApp webhook requests for both accounts"""
    # Use the default service for verification
    whatsapp_service = get_whatsapp_service(0)
    
    if request.method == 'GET':
        # Handle verification request
        challenge = whatsapp_service.verify_webhook(request.args)
        if challenge:
            return challenge
        else:
            return jsonify({"error": "Verification failed"}), 403
    
    elif request.method == 'POST':
        # Handle incoming messages
        try:
            data = request.json
            logger.info(f"Received webhook data: {data}")
            
            # Parse webhook data
            parsed_data = whatsapp_service.parse_webhook_data(data)
            
            # Process each message
            for message in parsed_data.get('messages', []):
                # Skip if message was already processed
                if message.get('id') and is_message_processed(message['id']):
                    logger.info(f"Skipping duplicate message {message['id']}")
                    continue
                
                process_message(message)
            
            return jsonify({"status": "success"}), 200
        
        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            return jsonify({"error": str(e)}), 500

def process_message(message):
    """
    Process an incoming WhatsApp message
    
    Args:
        message (dict): The parsed message data
    """
    # Extract message details
    from_number = message.get('from')
    message_type = message.get('type')
    account_index = message.get('account_index', 0)
    
    logger.info(f"Processing message from {from_number} of type {message_type} (account {account_index})")
    
    # Get services
    sentiment_service = get_sentiment_service()
    task_service = get_task_service()
    
    # Check if user exists, create if not
    user = User.get(from_number)
    if not user:
        # For new users, we'll use their phone number as name temporarily
        # and assign them to the correct account
        user = User.create(from_number, f"User_{from_number[-4:]}", 'user', account_index)
        logger.info(f"Created new user {from_number} for account {account_index}")
    
    # Get the WhatsApp service for this user's account
    whatsapp_service = get_whatsapp_service(user.account_index)
    
    # Update user's last active timestamp
    user.update_last_active()
    
    # Get text content based on message type
    text = None
    if message_type == 'text':
        text = message.get('text', '')
    elif message_type == 'voice':
        # Process voice note
        audio_url = message.get('voice_url')
        if audio_url:
            text = voice_service.process_voice_note(audio_url)
            if not text:
                whatsapp_service.send_message(
                    from_number,
                    "I couldn't understand your voice note. Could you please type your response or try recording again?"
                )
                return
            logger.info(f"Transcribed voice note: {text}")
    
    if not text:
        return
    
    # Analyze sentiment
    sentiment_score = sentiment_service.analyze(text)
    
    # Determine if this is a response to a check-in
    recent_checkins = CheckIn.get_for_user(from_number, limit=1)
    
    # Store the message as a check-in
    checkin = CheckIn.create(from_number, text, CheckIn.TYPE_DAILY, sentiment_score)
    
    # Update user's sentiment history
    user.add_sentiment_score(sentiment_score)
    
    # Process based on recent check-in context
    if recent_checkins:
        last_checkin = recent_checkins[0]
        
        # Check if this is a response to a compassion check-in
        if "This week may have been tough, and that's okay" in last_checkin.response or "A Moment for Self-Compassion" in last_checkin.response:
            # Process as win reflection
            response = process_win_reflection(user.user_id, text)
            whatsapp_service.send_message(from_number, response)
            logger.info(f"Processed win reflection from {from_number}")
            return
            
        # Weekly check-in response
        if "How are you feeling about the upcoming week?" in last_checkin.response:
            is_valid, feedback = validator.validate_feeling_response(text)
            if not is_valid:
                whatsapp_service.send_message(from_number, feedback)
                return
            process_weekly_response(user, text, sentiment_score)
        
        # Daily check-in response
        elif "How are you feeling today?" in last_checkin.response:
            is_valid, feedback = validator.validate_feeling_response(text)
            if not is_valid:
                whatsapp_service.send_message(from_number, feedback)
                return
            process_daily_response(user, text, sentiment_score)
        
        # Task list response
        elif "What tasks would you like to focus on today?" in last_checkin.response:
            is_valid, feedback = validator.validate_task_response(text)
            if not is_valid:
                whatsapp_service.send_message(from_number, feedback)
                return
            process_task_list(user, text)
        
        # Single task response
        elif "What's one small thing you'd like to accomplish today?" in last_checkin.response:
            is_valid, feedback = validator.validate_task_response(text)
            if not is_valid:
                whatsapp_service.send_message(from_number, feedback)
                return
            Task.create(user.user_id, text)
            whatsapp_service.send_message(
                from_number, 
                f"Great! I've added '{text}' as your task for today. You can update me on your progress anytime."
            )
        
        # Default response for other text messages
        else:
            # Basic response based on sentiment
            if sentiment_score < -0.3:
                # Negative sentiment
                response = "I'm sorry to hear you're not feeling great. What's one small task you'd like to accomplish today? Or would you prefer to rest?"
                whatsapp_service.send_message(from_number, response)
            elif -0.3 <= sentiment_score <= 0.3:
                # Neutral sentiment
                response = "Thanks for checking in. What tasks would you like to focus on today?"
                whatsapp_service.send_message(from_number, response)
            else:
                # Positive sentiment
                response = "Great to hear you're doing well! What tasks would you like to accomplish today?"
                whatsapp_service.send_message(from_number, response)
        
        logger.info(f"Processed message from {from_number} with sentiment {sentiment_score}")
    
    elif message_type == 'interactive':
        # Handle button responses
        button_id = message.get('button_id')
        
        if button_id:
            if button_id.startswith('task_'):
                # Handle task-related buttons
                parts = button_id.split('_')
                if len(parts) >= 3:
                    task_id = parts[1]
                    action = parts[2]
                    
                    task = Task.get(task_id)
                    if not task:
                        whatsapp_service.send_message(from_number, "Sorry, I couldn't find that task. Please try again.")
                        return
                    
                    if action == 'done':
                        task.update_status(Task.STATUS_DONE)
                        whatsapp_service.send_message(from_number, "Great job completing your task! 🎉")
                    
                    elif action == 'stuck':
                        task.update_status(Task.STATUS_STUCK)
                        hack = task_service.get_adhd_hack()
                        whatsapp_service.send_message(from_number, f"It's okay to struggle sometimes. Here's a strategy that might help: {hack}")
                    
                    elif action == 'progress':
                        task.update_status(Task.STATUS_IN_PROGRESS)
                        whatsapp_service.send_message(from_number, "Thanks for the update! Keep making progress at your own pace.")
            
            elif button_id == 'rest_today':
                handle_rest_request(user)
            
            elif button_id == 'one_task':
                handle_one_task_request(user)
            
            elif button_id == 'choose_one_task':
                handle_choose_one_task(user)
            
            elif button_id.startswith('select_task_'):
                # Handle selecting a specific task to focus on
                task_id = button_id.replace('select_task_', '')
                handle_task_selection(user, task_id)
            
            logger.info(f"Processed interactive message from {from_number} with button {button_id}")
    
    # Other message types can be handled as needed

def process_task_list(user, text):
    """
    Process a list of tasks from a user message
    
    Args:
        user (User): The user
        text (str): The message text containing tasks
    """
    whatsapp_service = get_whatsapp_service(user.account_index)
    
    # Split text by newlines, commas, or semicolons
    lines = text.replace(',', '\n').replace(';', '\n').split('\n')
    
    # Filter out empty lines
    tasks = [line.strip() for line in lines if line.strip()]
    
    if not tasks:
        whatsapp_service.send_message(
            user.user_id,
            "I didn't catch any tasks. Please list tasks you'd like to work on today."
        )
        return
    
    # Limit to 3 tasks for daily planners
    if user.planning_type == 'daily' and len(tasks) > 3:
        tasks = tasks[:3]
        whatsapp_service.send_message(
            user.user_id,
            "I've taken the first 3 tasks from your list to help you focus better."
        )
    
    # Create tasks
    created_tasks = []
    for task_description in tasks:
        task = Task.create(user.user_id, task_description)
        created_tasks.append(task)
    
    # Send confirmation
    if len(created_tasks) == 1:
        message = f"I've added your task: {created_tasks[0].description}"
    else:
        task_list = "\n".join([f"- {task.description}" for task in created_tasks])
        message = f"I've added your tasks:\n{task_list}"
    
    # Add task management options
    message += "\n\nYou can update me on your progress anytime. Would you like to work on these now?"
    
    whatsapp_service.send_message(user.user_id, message)
    
    # Send individual task buttons for each task
    for task in created_tasks:
        send_task_buttons(user, task) 