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
from app.cron.daily_checkin import process_daily_response, handle_task_button_response, handle_task_selection
from app.cron.end_of_day_checkin import process_end_of_day_response
from app.models.message import is_duplicate_message, record_message
from app.tools.voice_monitor import get_voice_monitor
import random
from datetime import datetime

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
            logger.info(f"Duplicate message detected: {message_id}")
            return jsonify({"status": "success", "message": "Duplicate message ignored"}), 200
        
        # Record this message
        record_message(message_id)
        
        # Log message details after duplicate check
        logger.info("----------------------------------------")
        logger.info(f"Processing new message:")
        logger.info(f"From: {from_number}")
        logger.info(f"Message ID: {message_id}")
        logger.info(f"Type: {message_type}")
        
        # Get the user
        user = User.get_or_create(from_number)
        
        # Check if this is a new user (just created)
        is_new_user = user.name.startswith('User ')  # Default name format for new users
        
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
        
        # Handle welcome flow for new users
        if is_new_user and message_type == 'text' and message_text and message_text.lower() in ['hi', 'hello', 'hey']:
            welcome_message = (
                "👋 Hi there! I'm your friendly accountability partner. I'm here to help you navigate your day, "
                "celebrate your wins (big or small), and work through any challenges.\n\n"
                "I'm designed to be flexible and supportive, especially on those days when things feel a bit much. "
                "What would you like me to call you?"
            )
            whatsapp_service.send_message(from_number, welcome_message)
            return jsonify({"status": "success", "message": "Welcome message sent"}), 200
        
        # Handle name response for new users
        if is_new_user and message_type == 'text' and message_text and not message_text.lower() in ['hi', 'hello', 'hey']:
            # Update user's name
            user.name = message_text.strip()
            user.update()
            
            # Send confirmation and next steps
            confirmation = (
                f"Nice to meet you, {user.name}! 👋\n\n"
                "I'll help you stay on track with your tasks and goals. Here's what I can do:\n"
                "• Daily check-ins to see how you're feeling\n"
                "• Task management and reminders\n"
                "• Weekly progress tracking\n"
                "• Support when you're feeling stuck\n\n"
                "Would you like to add your first task?"
            )
            whatsapp_service.send_message(from_number, confirmation)
            return jsonify({"status": "success", "message": "User name updated"}), 200
        
        elif message_type == 'interactive':
            # Handle button clicks
            interactive = message.get('interactive', {})
            if interactive.get('type') == 'button_reply':
                button_reply = interactive.get('button_reply', {})
                button_id = button_reply.get('id')
                logger.info(f"Button ID: {button_id}")
                
                # Handle task-related buttons
                if button_id in ['one_task', 'rest_today', 'support_needed']:
                    handle_task_button_response(user, button_id)
                    return jsonify({"status": "success", "message": "Task button response processed"}), 200
                
                # Handle other button types (if any)
                if button_id.startswith('select_task_'):
                    task_id = button_id.replace('select_task_', '')
                    handle_task_selection(user, task_id)
                    return jsonify({"status": "success", "message": "Task selection processed"}), 200
                
                logger.warning(f"Unknown button ID received: {button_id}")
                return jsonify({"status": "error", "message": "Unknown button type"}), 400
        
        elif message_type == 'audio':
            # Handle voice notes
            audio = message.get('audio', {})
            audio_url = audio.get('url')
            audio_duration = audio.get('duration', 0)  # Duration in seconds if available
            logger.info(f"Received voice note: {audio_url}, Duration: {audio_duration}s")
            
            # Get voice monitor for logging
            voice_monitor = get_voice_monitor()
            
            # Check if the voice note is too long (over 2 minutes)
            if audio_duration and audio_duration > 120:
                logger.warning(f"Voice note is too long: {audio_duration}s")
                                whatsapp_service.send_message(
                                    from_number,
                    "I noticed your voice note is quite long. For better transcription accuracy, please try to keep voice notes under 2 minutes."
                )
            
            if audio_url:
                # Transcribe the voice note
                voice_service = get_voice_service()
                message_text = voice_service.process_voice_note(audio_url)
                
                if message_text:
                    logger.info(f"Transcribed voice note: {message_text}")
                    is_voice_note = True
                    
                    # Store the transcription in user metadata for later feedback
                    user.set_metadata('last_transcription', message_text)
                    user.set_metadata('last_transcription_timestamp', datetime.now().isoformat())
                    
                    # Log successful transcription
                    voice_monitor.log_transcription(
                        user_id=from_number,
                        transcription=message_text,
                        success=True
                    )
                    
                    # Check for very short transcriptions that might indicate an issue
                    if len(message_text.split()) < 3:
                        logger.warning(f"Very short transcription: '{message_text}'")
                        # Send confirmation but with a hint that it might not be accurate
                        confirmation = f"✓ I heard: \"{message_text}\"\n\nIf this doesn't look right, you could try speaking a bit louder or in a quieter environment."
                    else:
                        # Normal confirmation
                        confirmation = f"✓ I heard: \"{message_text}\""
                    
                    whatsapp_service.send_message(from_number, confirmation)
                    
                    # Occasionally ask for feedback on transcription accuracy
                    if random.random() < 0.1:  # 10% chance
                        feedback_message = (
                            "Was the transcription accurate?\n\n"
                            "Reply with 'yes' if accurate, 'no' if inaccurate, or ignore this message."
                        )
                        whatsapp_service.send_message(from_number, feedback_message)
                else:
                    # Failed to transcribe
                    logger.error("Failed to transcribe voice note")
                    
                    # Log failed transcription
                    voice_monitor.log_transcription(
                        user_id=from_number,
                        transcription=None,
                        success=False
                    )
                    
                    whatsapp_service.send_message(
                        from_number,
                        "I couldn't understand your voice note. This might be due to background noise or audio quality. Could you please try again in a quieter environment, speak clearly, or send a text message instead?"
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
        
        # Get the most recent check-in to determine its type
        recent_checkins = CheckIn.get_for_user(user.user_id, limit=1, is_response=False)
        if recent_checkins:
            checkin_type = recent_checkins[0].type
            if checkin_type == CheckIn.TYPE_END_OF_DAY:
                process_end_of_day_response(user, message_text, sentiment_score)
            else:
                process_daily_response(user, message_text, sentiment_score)
        else:
            # Default to daily response if no recent check-in found
            process_daily_response(user, message_text, sentiment_score)
        
        # If this was a voice note, let's also remind the user that they can use voice notes for check-ins
        if is_voice_note and random.random() < 0.3:  # Only remind occasionally (30% chance)
            reminder = "💡 Remember, you can always send voice notes for your check-ins! It's a convenient way to share how you're feeling."
            whatsapp_service.send_message(from_number, reminder)
        
        # Add a message handler for transcription feedback
        if message_handler.is_transcription_feedback(message_text):
            # Get the last transcription for this user
            last_transcription = user.get_metadata('last_transcription')
            
            if last_transcription:
                feedback = 'accurate' if message_text.lower() in ['yes', 'y', 'correct', 'accurate'] else 'inaccurate'
                
                # Log the feedback
                voice_monitor = get_voice_monitor()
                voice_monitor.log_user_feedback(
                    user_id=from_number,
                    transcription=last_transcription,
                    feedback=feedback
                )
                
                # Thank the user for feedback
                    whatsapp_service.send_message(
                        from_number,
                    "Thank you for the feedback! It helps us improve our voice recognition."
                    )
                return jsonify({"status": "success", "message": "Feedback processed"}), 200
        
        return jsonify({"status": "success", "message": "Message processed"}), 200
        
    except Exception as e:
        logger.error(f"Error in webhook: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500