from flask import Blueprint, request, jsonify
from firebase_admin import firestore
import logging
from app.services.whatsapp import get_whatsapp_service
from app.services.tasks import get_task_service
from app.models.user import User
from app.models.task import Task
from config.firebase_config import get_db

logger = logging.getLogger(__name__)

# Create the webhook blueprint
webhook_bp = Blueprint('webhook', __name__)

@webhook_bp.route('/whatsapp', methods=['POST'])
def whatsapp_webhook():
    """Handle incoming WhatsApp messages"""
    try:
        # Get message data
        data = request.get_json()
        logger.info(f"Received webhook data: {data}")
        
        # Extract message details
        entry = data.get('entry', [{}])[0]
        changes = entry.get('changes', [{}])[0]
        value = changes.get('value', {})
        messages = value.get('messages', [])
        
        if not messages:
            return jsonify({"status": "success", "message": "No messages to process"}), 200
            
        message = messages[0]
        from_number = message.get('from')
        message_id = message.get('id')
        message_type = message.get('type')
        
        # Check for duplicate messages
        if is_duplicate_message(message_id):
            logger.info(f"Skipping duplicate message {message_id}")
            return jsonify({"status": "success", "message": "Duplicate message skipped"}), 200
        
        # Get or create user
        try:
            user = User.get_or_create(from_number)
        except Exception as e:
            logger.error(f"Error getting/creating user: {e}")
            return jsonify({"status": "error", "message": "User processing error"}), 500
        
        logger.info(f"Processing message from {from_number} of type {message_type} (account {user.account_index})")
        
        # Get services
        whatsapp_service = get_whatsapp_service()
        task_service = get_task_service()
        
        # Handle different message types
        if message_type == 'text':
            text = message.get('text', {}).get('body', '').strip()
            
            # Handle button actions
            if 'button' in data:
                try:
                    button = data['button']
                    action = button.get('action')
                    payload = button.get('payload', {})
                    
                    if action == 'done':
                        task_id = payload.get('task_id')
                        task = Task.get(task_id)
                        if task:
                            task.update_status(Task.STATUS_DONE)
                            whatsapp_service.send_message(from_number, "Great job completing your task! 🎉")
                            task_service.log_task_completion(user.user_id, task_id)
                    
                    elif action == 'stuck':
                        task_id = payload.get('task_id')
                        task = Task.get(task_id)
                        if task:
                            task.update_status(Task.STATUS_STUCK)
                            
                            # Store that the user is stuck for follow-up
                            user.task_needs_followup = task_id
                            user.update()
                            
                            try:
                                # Get a personalized hack
                                hack, is_personalized = task_service.get_adhd_hack(user.user_id, task.description)
                                
                                # Store the current hack for this task
                                user.current_hack = {
                                    'task_id': task_id,
                                    'hack': hack,
                                    'attempts': []  # Track which hacks were tried
                                }
                                user.update()
                                
                                # Send empathetic response with the hack
                                message = (
                                    f"I understand you're stuck with this task. That's completely normal with executive function differences. "
                                    f"Let's try this strategy:\n\n"
                                    f"💡 {hack}"
                                )
                                if is_personalized:
                                    message += "\n(This strategy has worked well for you before!)"
                                
                                whatsapp_service.send_message(from_number, message)
                                
                                # Send action buttons
                                buttons = [
                                    {"id": f"hack_{task_id}_try_another", "title": "Try Another Hack"},
                                    {"id": f"hack_{task_id}_helped", "title": "This Helped!"},
                                    {"id": f"hack_{task_id}_break_down", "title": "Break Down Task"}
                                ]
                                
                                whatsapp_service.send_interactive_buttons(
                                    from_number,
                                    "How would you like to proceed?",
                                    buttons
                                )
                            except Exception as e:
                                logger.error(f"Error getting ADHD hack: {e}")
                                whatsapp_service.send_message(
                                    from_number,
                                    "I'm having trouble accessing my strategies right now. Let's try breaking down your task into smaller steps instead."
                                )
                    
                    elif action == 'try_another_hack':
                        task_id = payload.get('task_id')
                        task = Task.get(task_id)
                        
                        if not task:
                            whatsapp_service.send_message(from_number, "Sorry, I couldn't find that task. Please try marking it as stuck again.")
                            return jsonify({"status": "error", "message": "Task not found"}), 404
                        
                        try:
                            # Get current hack attempts for this task
                            current_hack = getattr(user, 'current_hack', {})
                            if current_hack.get('task_id') != task_id:
                                # Reset if it's a different task
                                current_hack = {
                                    'task_id': task_id,
                                    'attempts': []
                                }
                            
                            # Get a new hack, excluding previously tried ones
                            hack, is_personalized = task_service.get_adhd_hack(
                                user.user_id,
                                task.description,
                                exclude_hacks=current_hack.get('attempts', [])
                            )
                            
                            # Update current hack
                            current_hack['hack'] = hack
                            current_hack['attempts'].append(hack)
                            user.current_hack = current_hack
                            user.update()
                            
                            # Send the new hack
                            message = f"Let's try a different approach:\n\n💡 {hack}"
                            if is_personalized:
                                message += "\n(This strategy has worked well for you before!)"
                            
                            whatsapp_service.send_message(from_number, message)
                            
                            # Send action buttons again
                            buttons = [
                                {"id": f"hack_{task_id}_try_another", "title": "Try Another Hack"},
                                {"id": f"hack_{task_id}_helped", "title": "This Helped!"},
                                {"id": f"hack_{task_id}_break_down", "title": "Break Down Task"}
                            ]
                            
                            whatsapp_service.send_interactive_buttons(
                                from_number,
                                "How would you like to proceed?",
                                buttons
                            )
                        except Exception as e:
                            logger.error(f"Error getting next hack: {e}")
                            whatsapp_service.send_message(
                                from_number,
                                "I'm having trouble getting another strategy right now. Would you like to try breaking down the task instead?"
                            )
                    
                    elif action == 'hack_helped':
                        task_id = payload.get('task_id')
                        task = Task.get(task_id)
                        
                        if not task:
                            whatsapp_service.send_message(from_number, "Sorry, I couldn't find that task. Please try marking it as stuck again.")
                            return jsonify({"status": "error", "message": "Task not found"}), 404
                        
                        try:
                            # Get the successful hack
                            current_hack = getattr(user, 'current_hack', {})
                            if current_hack.get('task_id') == task_id and current_hack.get('hack'):
                                # Log the successful strategy
                                task_service.log_successful_strategy(
                                    user.user_id,
                                    task_id,
                                    current_hack['hack'],
                                    task.description
                                )
                                
                                # Clear the current hack
                                user.current_hack = None
                                user.update()
                                
                                # Update task status to in progress
                                task.update_status(Task.STATUS_IN_PROGRESS)
                                
                                # Send encouraging message
                                message = (
                                    "That's great! I'm glad this strategy helped. "
                                    "I'll remember this for similar tasks in the future. "
                                    "You've got this! 💪"
                                )
                                whatsapp_service.send_message(from_number, message)
                        except Exception as e:
                            logger.error(f"Error processing successful hack: {e}")
                            whatsapp_service.send_message(
                                from_number,
                                "I'm glad the strategy helped! Let's keep moving forward with your task."
                            )
                    
                    elif action == 'progress':
                        task_id = payload.get('task_id')
                        task = Task.get(task_id)
                        if task:
                            task.update_status(Task.STATUS_IN_PROGRESS)
                            whatsapp_service.send_message(from_number, "Thanks for the update! Keep making progress at your own pace.")
                except Exception as e:
                    logger.error(f"Error processing button action: {e}")
                    whatsapp_service.send_message(
                        from_number,
                        "I'm having trouble processing your action. Please try again in a moment."
                    )
            
            # Handle text responses
            elif hasattr(user, 'task_needs_followup') and user.task_needs_followup:
                try:
                    task_id = user.task_needs_followup
                    # Store the obstacle
                    task_service.log_task_obstacle(user.user_id, task_id, text)
                    
                    # Clear the follow-up flag
                    user.task_needs_followup = None
                    user.update()
                    
                    # Thank the user for sharing
                    response = (
                        "Thank you for explaining the obstacle. I've recorded this to help provide "
                        "better support in the future. Remember that challenges are normal, especially "
                        "with executive function differences."
                    )
                    whatsapp_service.send_message(from_number, response)
                except Exception as e:
                    logger.error(f"Error processing obstacle response: {e}")
                    whatsapp_service.send_message(
                        from_number,
                        "Thank you for sharing. I'm having some trouble right now, but let's focus on moving forward with your task."
                    )
            else:
                # Handle regular text message
                try:
                    # Process the message using conversation handler
                    message_handler = MessageHandler()
                    message_handler.handle_message(user, text)
                except Exception as e:
                    logger.error(f"Error processing text message: {e}")
                    whatsapp_service.send_message(
                        from_number,
                        "I'm having trouble understanding your message right now. Could you try rephrasing it?"
                    )
        
        # Record message for duplicate checking
        record_message(message_id)
        return jsonify({"status": "success"}), 200
        
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
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