from flask import Blueprint, request, jsonify, url_for
from firebase_admin import firestore
import logging
import os
from app.services.whatsapp import get_whatsapp_service
from app.services.tasks import get_task_service
from app.models.user import User
from app.models.task import Task
from config.firebase_config import get_db
from app.services.message_handler import MessageHandler
from app.services.voice import get_voice_service
from app.services.sentiment import get_sentiment_service
from app.cron.daily_checkin import process_daily_response
from app.models.message import is_duplicate_message
import random

logger = logging.getLogger(__name__)

# Create the webhook blueprint without url_prefix
webhook_bp = Blueprint('webhook', __name__)

VERIFY_TOKEN = "odinma_accountability_webhook"  # This should match what you set in the WhatsApp dashboard

@webhook_bp.route('/webhook', methods=['GET', 'POST'])
@webhook_bp.route('/webhook/', methods=['GET', 'POST'])
def whatsapp_webhook():
    """Handle incoming WhatsApp messages and webhook verification"""
    logger.info("----------------------------------------")
    logger.info("Webhook endpoint hit")
    logger.info(f"Request method: {request.method}")
    logger.info(f"Request args: {request.args}")
    logger.info(f"Request URL: {request.url}")
    
    if request.method == 'GET':
        # Handle webhook verification
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        
        logger.info(f"Verification request: mode={mode}, token={token}, challenge={challenge}")
        
        # If this is a verification request
        if mode == 'subscribe' and token == VERIFY_TOKEN:
            logger.info("Webhook verified successfully")
            return str(challenge), 200
        else:
            logger.error(f"Webhook verification failed. Expected token: {VERIFY_TOKEN}, Received token: {token}")
            return 'Invalid verification token', 403

    # Handle POST requests (actual messages)
    try:
        # Get message data
        data = request.get_json()
        
        # Extract message details
        entry = data.get('entry', [{}])[0] if data and 'entry' in data else {}
        changes = entry.get('changes', [{}])[0] if entry and 'changes' in entry else {}
        value = changes.get('value', {})
        messages = value.get('messages', [])
        
        if not messages:
            logger.info("No messages to process")
            return jsonify({"status": "success", "message": "No messages to process"}), 200
            
        message = messages[0]
        from_number = message.get('from')
        message_id = message.get('id')
        message_type = message.get('type')
        
        # Check for duplicate messages first
        if is_duplicate_message(message_id):
            logger.info(f"Skipping duplicate message {message_id} from {from_number}")
            return jsonify({"status": "success", "message": "Duplicate message skipped"}), 200
        
        # Log message details after duplicate check
        logger.info("----------------------------------------")
        logger.info(f"Processing new message:")
        logger.info(f"From: {from_number}")
        logger.info(f"Message ID: {message_id}")
        logger.info(f"Type: {message_type}")
        
        # Get the user
        user = User.get_or_create(from_number)
        
        # Update user's last active time
        user.update_last_active()
        
        # Get WhatsApp service
        whatsapp_service = get_whatsapp_service(user.account_index)
        
        # Initialize message text
        message_text = None
        is_voice_note = False
        
        # Handle different message types
        if message_type == 'text':
            message_text = message.get('text', {}).get('body', '').strip()
            logger.info(f"Message Content: {message_text}")
            
        elif message_type == 'interactive':
            # Handle button clicks
            interactive = message.get('interactive', {})
            if interactive.get('type') == 'button_reply':
                button_reply = interactive.get('button_reply', {})
                button_id = button_reply.get('id')
                logger.info(f"Button ID: {button_id}")
                
                # Handle the button response
                from app.routes.button_handler import handle_button_response
                handle_button_response(user, button_id)
                return jsonify({"status": "success", "message": "Button response processed"}), 200
        
        elif message_type == 'audio':
            # Handle voice notes
            audio = message.get('audio', {})
            audio_url = audio.get('url')
            logger.info(f"Received voice note: {audio_url}")
            
            if audio_url:
                # Transcribe the voice note
                voice_service = get_voice_service()
                message_text = voice_service.process_voice_note(audio_url)
                
                if message_text:
                    logger.info(f"Transcribed voice note: {message_text}")
                    is_voice_note = True
                    
                    # Send a confirmation of the transcription
                    confirmation = f"✓ I heard: \"{message_text}\""
                    whatsapp_service.send_message(from_number, confirmation)
                else:
                    # Failed to transcribe
                    logger.error("Failed to transcribe voice note")
                    whatsapp_service.send_message(
                        from_number, 
                        "I couldn't understand your voice note. Could you please try again or send a text message?"
                    )
                    return jsonify({"status": "error", "message": "Voice transcription failed"}), 200
        
        # If we don't have any message text at this point, return
        if not message_text:
            logger.info("No message text to process")
            return jsonify({"status": "success", "message": "No message text to process"}), 200
        
        # Try to handle as a task update command first
        message_handler = MessageHandler()
        if message_handler.handle_task_update(user, message_text):
            return jsonify({"status": "success", "message": "Task update processed"}), 200
        
        if message_handler.handle_message(user, message_text):
            return jsonify({"status": "success", "message": "Message handled by MessageHandler"}), 200
        
        # If not a command, process as a response to check-in
        sentiment_service = get_sentiment_service()
        sentiment_score = sentiment_service.analyze(message_text)
        
        # Update user's sentiment history
        user.add_sentiment_score(sentiment_score)
        
        # Process the response
        process_daily_response(user, message_text, sentiment_score)
        
        # If this was a voice note, let's also remind the user that they can use voice notes for check-ins
        if is_voice_note and random.random() < 0.3:  # Only remind occasionally (30% chance)
            reminder = "💡 Remember, you can always send voice notes for your check-ins! It's a convenient way to share how you're feeling."
            whatsapp_service.send_message(from_number, reminder)
        
        return jsonify({"status": "success", "message": "Message processed"}), 200
        
    except Exception as e:
        logger.error(f"Error in webhook: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

def is_duplicate_message(message_id):
    """Check if a message has been processed before"""
    try:
        db = get_db()
        doc = db.collection('processed_messages').document(message_id).get()
        return doc.exists
    except Exception as e:
        logger.error(f"Error checking duplicate message: {e}")
        return False

def record_message(message_id):
    """Record a message as processed"""
    try:
        db = get_db()
        db.collection('processed_messages').document(message_id).set({
            'timestamp': firestore.SERVER_TIMESTAMP
        })
    except Exception as e:
        logger.error(f"Error recording message: {e}") 