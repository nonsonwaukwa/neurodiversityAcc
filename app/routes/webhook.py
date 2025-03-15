from flask import Blueprint, request, jsonify
from app.services.whatsapp import get_whatsapp_service, get_whatsapp_service_for_number
from app.services.sentiment import get_sentiment_service
from app.services.tasks import get_task_service
from app.models.user import User
from app.models.checkin import CheckIn
import json
import logging
import os

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create blueprint
webhook_bp = Blueprint('webhook', __name__)

@webhook_bp.route('/webhook', methods=['GET', 'POST'])
def webhook():
    """Handle WhatsApp webhook requests for both accounts"""
    # Use the default service for verification
    whatsapp_service = get_whatsapp_service(0)
    
    if request.method == 'GET':
        # Enhanced logging for webhook verification
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        expected_token = os.environ.get('WHATSAPP_VERIFY_TOKEN')
        
        logger.info(f"Webhook verification request received")
        logger.info(f"hub.mode: {mode}")
        logger.info(f"hub.verify_token (received): {token}")
        logger.info(f"Expected verify token from env: {expected_token}")
        logger.info(f"hub.challenge: {challenge}")
        
        # Handle verification request
        if mode == 'subscribe' and token == expected_token:
            logger.info("Webhook verification successful")
            return challenge
        else:
            logger.error(f"Webhook verification failed. Token match: {token == expected_token}")
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
                process_message(message)
            
            return jsonify({"status": "success"}), 200
        
        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            return jsonify({"error": str(e)}), 500

@webhook_bp.route('/test-verify-token', methods=['GET'])
def test_verify_token():
    """Test route to check if the webhook verify token is accessible"""
    # Get the token from environment
    token = os.environ.get('WHATSAPP_VERIFY_TOKEN')
    # Return details about the token
    return jsonify({
        "token_exists": token is not None,
        "token_length": len(token) if token else 0,
        "token_first_char": token[0] if token else None,
        "token_last_char": token[-1] if token else None
    })

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
        user = User.create(from_number, f"User_{from_number[-4:]}", 'AI', account_index)
        logger.info(f"Created new user {from_number} for account {account_index}")
    
    # Get the WhatsApp service for this user's account
    whatsapp_service = get_whatsapp_service(user.account_index)
    
    # Update user's last active timestamp
    user.update_last_active()
    
    # Process based on message type
    if message_type == 'text':
        text = message.get('text', '')
        
        # Analyze sentiment
        sentiment_score = sentiment_service.analyze(text)
        
        # Store the message as a check-in
        checkin = CheckIn.create(from_number, text, CheckIn.TYPE_DAILY, sentiment_score)
        
        # Update user's sentiment history
        user.add_sentiment_score(sentiment_score)
        
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
        
        logger.info(f"Processed text message from {from_number} with sentiment {sentiment_score}")
    
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
                    
                    if action == 'done':
                        task_service.update_task_status(task_id, 'Done')
                        whatsapp_service.send_message(from_number, "Great job completing your task! 🎉")
                    
                    elif action == 'stuck':
                        task_service.update_task_status(task_id, 'Stuck')
                        hack = task_service.get_adhd_hack(task_id)
                        whatsapp_service.send_message(from_number, f"It's okay to struggle sometimes. Here's a strategy that might help: {hack}")
                    
                    elif action == 'progress':
                        task_service.update_task_status(task_id, 'In Progress')
                        whatsapp_service.send_message(from_number, "Thanks for the update! Keep making progress at your own pace.")
            
            elif button_id == 'rest_today':
                whatsapp_service.send_message(from_number, "That's absolutely fine. Rest is important. I'll check in with you tomorrow.")
            
            elif button_id == 'one_task':
                whatsapp_service.send_message(from_number, "What's one small thing you'd like to accomplish today?")
            
            logger.info(f"Processed interactive message from {from_number} with button {button_id}")
    
    # Other message types can be handled as needed 