from flask import Blueprint, request, jsonify
from app.models.user import User
from app.services.nlp import get_nlp_service
from app.services.message_handler import MessageHandler
from app.cron.daily_checkin import process_daily_response
import logging

# Set up logger
logger = logging.getLogger(__name__)

# Create blueprint
whatsapp_bp = Blueprint('whatsapp', __name__)

@whatsapp_bp.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming WhatsApp messages"""
    try:
        data = request.json
        
        # Extract message data
        message = data.get('message', {})
        user_id = message.get('from')
        message_text = message.get('text', {}).get('body', '')
        
        if not user_id or not message_text:
            return jsonify({"status": "error", "message": "Invalid message format"}), 400
        
        # Get or create user
        user = User.get(user_id)
        if not user:
            # Handle new user registration
            return jsonify({"status": "error", "message": "User not registered"}), 404
        
        # Update user's last active timestamp
        user.update_last_active()
        
        # Try to handle as a task update command first
        message_handler = MessageHandler()
        if message_handler.handle_message(user, message_text):
            return jsonify({"status": "success"}), 200
        
        # If not a command, process as a normal message
        nlp_service = get_nlp_service()
        sentiment_score = nlp_service.analyze_sentiment(message_text)
        
        # Process the response
        process_daily_response(user, message_text, sentiment_score)
        
        return jsonify({"status": "success"}), 200
        
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500 