import re
from datetime import datetime
import logging
from app.models.task import Task
from app.services.whatsapp import get_whatsapp_service
from app.services.tasks import get_task_service
from app.services.analytics import get_analytics_service
from app.services.conversation_analytics import ConversationAnalyticsService

logger = logging.getLogger(__name__)

class MessageHandler:
    """Service for handling incoming messages and commands"""

    # Command patterns - making emojis optional and commands case-insensitive
    TASK_DONE_PATTERN = r"^(?:✅\s*)?(?:done|complete|finished)\s+(\d+)$"
    TASK_PROGRESS_PATTERN = r"^(?:🔄\s*)?(?:progress|doing|working|started)\s+(\d+)$"
    TASK_STUCK_PATTERN = r"^(?:❌\s*)?(?:stuck|help|blocked)\s+(\d+)$"

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
                
                response = f"🎉 Great job completing: {task.description}"
                
            elif new_status == Task.STATUS_IN_PROGRESS:
                response = f"👍 Marked as in progress: {task.description}"
                
            else:  # STUCK
                response = (
                    f"I understand you're stuck with: {task.description}\n\n"
                    "Would you like to:"
                )
                
                # Offer help options
                buttons = [
                    {"id": "break_down", "title": "Break it down"},
                    {"id": "modify_task", "title": "Modify task"},
                    {"id": "get_help", "title": "Get help"}
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
                        "🎊 Wow! You've completed all your tasks for today!\n"
                        "Take a moment to celebrate this achievement. Would you like to:"
                    )
                    
                    buttons = [
                        {"id": "add_more_tasks", "title": "Add more tasks"},
                        {"id": "done_for_today", "title": "Done for today"}
                    ]
                    
                    whatsapp_service.send_interactive_buttons(user.user_id, celebration, buttons)
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing task update for user {user.user_id}: {e}")
            whatsapp_service.send_message(
                user.user_id,
                "Sorry, I couldn't process that task update. Please try again or contact support if the problem persists."
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
                "You don't have any active tasks. Would you like to add some?"
            )
            return
        
        # Sort tasks by creation date
        tasks.sort(key=lambda t: t.created_at)
        
        # Format task list with numbers and status indicators
        message = "Your active tasks:\n\n"
        for i, task in enumerate(tasks, 1):
            status_indicator = "⏳"  # Pending
            if task.status == Task.STATUS_IN_PROGRESS:
                status_indicator = "🔄"
            elif task.status == Task.STATUS_STUCK:
                status_indicator = "❌"
                
            message += f"{i}. {status_indicator} {task.description}\n"
        
        message += "\nUpdate task status with:\n"
        message += "DONE [number] - Mark as complete\n"
        message += "PROGRESS [number] - Mark as in progress\n"
        message += "STUCK [number] - Mark as stuck"
        
        whatsapp_service.send_message(user.user_id, message)
    
    @staticmethod
    def handle_message(user, message_text):
        """
        Handle an incoming message
        
        Args:
            user (User): The user sending the message
            message_text (str): The message text
            
        Returns:
            bool: Whether the message was handled
        """
        # First check for task update commands
        if MessageHandler.handle_task_update(user, message_text):
            return True
            
        # Check for task list request
        if message_text.lower().strip() in ['tasks', 'list', 'show tasks']:
            MessageHandler.list_active_tasks(user)
            return True
        
        return False  # Message wasn't handled 