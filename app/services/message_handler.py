import re
from datetime import datetime
import logging
from app.models.task import Task
from app.services.whatsapp import get_whatsapp_service
from app.services.tasks import get_task_service
from app.services.analytics import get_analytics_service
from app.services.conversation_analytics import ConversationAnalyticsService
from app.models.checkin import CheckIn

logger = logging.getLogger(__name__)

class MessageHandler:
    """Service for handling incoming messages and commands"""

    # Command patterns - making emojis optional and commands case-insensitive
    TASK_DONE_PATTERN = r"^(?:✅\s*)?(?:done|complete|finished)\s+(\d+)$"
    TASK_PROGRESS_PATTERN = r"^(?:🔄\s*)?(?:progress|doing|working|started)\s+(\d+)$"
    TASK_STUCK_PATTERN = r"^(?:❌\s*)?(?:stuck|help|blocked)\s+(\d+)$"
    
    # Transcription feedback patterns
    TRANSCRIPTION_FEEDBACK_PATTERN = r"^(?:yes|no|y|n|correct|incorrect|accurate|inaccurate)$"

    @staticmethod
    def handle_task_update(user, message_text):
        """
        Handle task update commands
        
        Args:
            user (User): The user sending the command
            message_text (str): The command text
            
        Returns:
            bool: Whether the message was a task update command
        """
        # Strip whitespace and normalize
        message = message_text.strip().lower()
        
        # Check for task update patterns
        done_match = re.match(MessageHandler.TASK_DONE_PATTERN, message, re.IGNORECASE)
        progress_match = re.match(MessageHandler.TASK_PROGRESS_PATTERN, message, re.IGNORECASE)
        stuck_match = re.match(MessageHandler.TASK_STUCK_PATTERN, message, re.IGNORECASE)
        
        if not any([done_match, progress_match, stuck_match]):
            return False
            
        # Get services
        whatsapp_service = get_whatsapp_service(user.account_index)
        task_service = get_task_service()
        analytics_service = get_analytics_service()
        conversation_analytics = ConversationAnalyticsService()
        
        try:
            # Get task number and find corresponding task
            task_number = None
            new_status = None
            
            if done_match:
                task_number = int(done_match.group(1))
                new_status = Task.STATUS_DONE
            elif progress_match:
                task_number = int(progress_match.group(1))
                new_status = Task.STATUS_IN_PROGRESS
            elif stuck_match:
                task_number = int(stuck_match.group(1))
                new_status = Task.STATUS_STUCK
            
            # Get user's active tasks
            tasks = Task.get_for_user(user.user_id, status=[
                Task.STATUS_PENDING,
                Task.STATUS_IN_PROGRESS,
                Task.STATUS_STUCK
            ])
            
            # Sort tasks by creation date
            tasks.sort(key=lambda t: t.created_at)
            
            if task_number < 1 or task_number > len(tasks):
                whatsapp_service.send_message(
                    user.user_id,
                    f"❌ Task number {task_number} not found. You have {len(tasks)} active tasks."
                )
                return True
            
            # Get the task (subtract 1 as users see 1-based numbering)
            task = tasks[task_number - 1]
            
            # Update task status
            task.update_status(new_status)
            
            # Log completion if task is done
            if new_status == Task.STATUS_DONE:
                analytics_service.log_task_completion(
                    user.user_id,
                    task.task_id,
                    task.description
                )
                
                # Log themes for completion message
                conversation_analytics.log_conversation_themes(
                    user.user_id,
                    f"Completed task: {task.description}",
                    'task_completion'
                )
                
                response = f"🌟 That's wonderful! You completed: {task.description}\nEven small steps are meaningful progress - this is something to celebrate."
                
            elif new_status == Task.STATUS_IN_PROGRESS:
                response = f"💫 I've noted you're working on: {task.description}\nStarting is often the hardest part - I appreciate your effort."
                
            else:  # STUCK
                response = (
                    f"I hear that you're finding '{task.description}' challenging, and that's completely okay and normal.\n\n"
                    "Would you like to explore any of these gentle options:"
                )
                
                # Offer help options
                buttons = [
                    {"id": "break_down", "title": "Break into smaller steps"},
                    {"id": "modify_task", "title": "Adjust the task"},
                    {"id": "get_help", "title": "Explore support options"}
                ]
                
                whatsapp_service.send_interactive_buttons(user.user_id, response, buttons)
                return True
            
            whatsapp_service.send_message(user.user_id, response)
            
            # If they completed all tasks, celebrate
            if new_status == Task.STATUS_DONE:
                remaining_tasks = Task.get_for_user(
                    user.user_id,
                    status=[Task.STATUS_PENDING, Task.STATUS_IN_PROGRESS, Task.STATUS_STUCK]
                )
                
                if not remaining_tasks:
                    celebration = (
                        "✨ What a beautiful moment! You've completed all the intentions you set.\n"
                        "This is truly something to celebrate and honor. Your effort matters, regardless of how small the tasks may have seemed. Would you like to:"
                    )
                    
                    buttons = [
                        {"id": "add_more_tasks", "title": "Add a new intention"},
                        {"id": "done_for_today", "title": "Rest & celebrate"}
                    ]
                    
                    whatsapp_service.send_interactive_buttons(user.user_id, celebration, buttons)
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing task update for user {user.user_id}: {e}")
            whatsapp_service.send_message(
                user.user_id,
                "I'm sorry, I couldn't process that update. This is on my end, not yours. Could we try that again in a slightly different way?"
            )
            return True
    
    @staticmethod
    def list_active_tasks(user):
        """
        Send a list of active tasks to the user
        
        Args:
            user (User): The user to list tasks for
        """
        whatsapp_service = get_whatsapp_service(user.account_index)
        
        # Get active tasks
        tasks = Task.get_for_user(user.user_id, status=[
            Task.STATUS_PENDING,
            Task.STATUS_IN_PROGRESS,
            Task.STATUS_STUCK
        ])
        
        if not tasks:
            whatsapp_service.send_message(
                user.user_id,
                "You don't have any active intentions at the moment, which is perfectly okay. Would you like to add something small that might feel nurturing or helpful?"
            )
            return
        
        # Sort tasks by creation date
        tasks.sort(key=lambda t: t.created_at)
        
        # Format task list with numbers and status indicators
        message = "Here are the intentions you've set (there's no pressure to complete all or any of these - they're just gentle guides):\n\n"
        for i, task in enumerate(tasks, 1):
            status_indicator = "⏳"  # Pending
            if task.status == Task.STATUS_IN_PROGRESS:
                status_indicator = "🔄"
            elif task.status == Task.STATUS_STUCK:
                status_indicator = "💜"
                
            message += f"{i}. {status_indicator} {task.description}\n"
        
        message += "\nIf you'd like to update how things are going, you could use:\n"
        message += "DONE [number] - Celebrate completing this\n"
        message += "PROGRESS [number] - Note you've started this\n"
        message += "STUCK [number] - Let me know this feels challenging"
        
        whatsapp_service.send_message(user.user_id, message)
    
    @staticmethod
    def is_transcription_feedback(message_text):
        """
        Check if a message is feedback on a voice transcription
        
        Args:
            message_text (str): The message text
            
        Returns:
            bool: Whether the message is transcription feedback
        """
        if not message_text:
            return False
            
        # Clean and normalize the text
        message = message_text.strip().lower()
        
        # Check if it matches feedback pattern
        return bool(re.match(MessageHandler.TRANSCRIPTION_FEEDBACK_PATTERN, message, re.IGNORECASE))
    
    @staticmethod
    def handle_message(user, message_text):
        """
        Handle an incoming message
        
        Args:
            user (User): The user who sent the message
            message_text (str): The message text
            
        Returns:
            bool: Whether the message was handled
        """
        # First check if this is a task update command
        if MessageHandler.handle_task_update(user, message_text):
            return True
            
        # Check if this is transcription feedback
        if MessageHandler.is_transcription_feedback(message_text):
            return True
            
        # Check if this is a response to a check-in
        recent_checkins = CheckIn.get_for_user(user.user_id, limit=1, is_response=False)
        if recent_checkins:
            recent_checkin = recent_checkins[0]
            # Only process as a check-in response if it's from today
            today = datetime.now(timezone.utc).date()
            checkin_date = recent_checkin.created_at.date() if recent_checkin.created_at else None
            
            if checkin_date and checkin_date == today:
                # Check if the recent check-in was a system message asking for a response
                if any(phrase in recent_checkin.response for phrase in [
                    "How are you feeling",
                    "A gentle check-in about the week ahead",
                    "I hope you've been able to rest",
                    "Whatever you're experiencing is"
                ]):
                    # This is a response to a check-in, don't treat it as a task
                    return False
            
        # If we get here, check if this should be treated as a new task
        if user.name and not user.name.startswith('User '):  # User has set their name
            # Get active tasks
            active_tasks = Task.get_for_user(user.user_id, status=[
                Task.STATUS_PENDING,
                Task.STATUS_IN_PROGRESS,
                Task.STATUS_STUCK
            ])
            
            # If no active tasks, treat this as a new task
            if not active_tasks:
                whatsapp_service = get_whatsapp_service(user.account_index)
                
                # Create the task
                task = Task.create(
                    user_id=user.user_id,
                    description=message_text.strip(),
                    status=Task.STATUS_PENDING
                )
                
                # Send confirmation
                confirmation = (
                    f"✨ I've added your intention: {task.description}\n\n"
                    "You can update how things are going by using:\n"
                    "• DONE [number] - When you complete something\n"
                    "• PROGRESS [number] - When you start working on it\n"
                    "• STUCK [number] - If you need some support\n\n"
                    "Would you like to add another intention?"
                )
                
                whatsapp_service.send_message(user.user_id, confirmation)
                return True
        
        return False  # Message wasn't handled 