import random
from datetime import datetime
from app.models.task import Task
from app.models.user import User
from config.settings import Config

class TaskService:
    """Service for managing tasks and providing ADHD-friendly strategies"""
    
    def __init__(self):
        """Initialize the task service"""
        self.adhd_hacks = Config.ADHD_HACKS
    
    def create_task(self, user_id, description, category=Task.CATEGORY_OTHER):
        """
        Create a new task for a user
        
        Args:
            user_id (str): The user's ID
            description (str): The task description
            category (str): The task category
            
        Returns:
            Task: The created task
        """
        # Ensure the user exists
        user = User.get(user_id)
        if not user:
            raise ValueError(f"User with ID {user_id} not found")
        
        # Create the task
        task = Task.create(user_id, description, category)
        
        return task
    
    def update_task_status(self, task_id, new_status):
        """
        Update a task's status
        
        Args:
            task_id (str): The task's ID
            new_status (str): The new status
            
        Returns:
            Task: The updated task
        """
        task = Task.get(task_id)
        if not task:
            raise ValueError(f"Task with ID {task_id} not found")
        
        task.update_status(new_status)
        
        return task
    
    def get_user_tasks(self, user_id, status=None, limit=None):
        """
        Get tasks for a specific user
        
        Args:
            user_id (str): The user's ID
            status (str, optional): Filter by task status
            limit (int, optional): Maximum number of tasks to retrieve
            
        Returns:
            list: List of Task objects
        """
        return Task.get_for_user(user_id, status, limit)
    
    def get_adhd_hack(self, task_id=None):
        """
        Get a random ADHD-friendly strategy
        
        Args:
            task_id (str, optional): The task ID to mark as having used a hack
            
        Returns:
            str: An ADHD-friendly strategy
        """
        hack = random.choice(self.adhd_hacks)
        
        # If task_id is provided, mark that a hack was used for this task
        if task_id:
            task = Task.get(task_id)
            if task:
                task.mark_hack_used()
        
        return hack
    
    def parse_task_update(self, message_text):
        """
        Parse a task update message from the user
        
        Args:
            message_text (str): The message text
            
        Returns:
            dict: A dictionary with the task ID and new status
        """
        # This is a basic implementation that needs to be expanded based on your actual message format
        message_lower = message_text.lower()
        
        status = None
        if "done" in message_lower or "✅" in message_lower:
            status = Task.STATUS_DONE
        elif "stuck" in message_lower or "❌" in message_lower:
            status = Task.STATUS_STUCK
        elif "progress" in message_lower or "🔄" in message_lower:
            status = Task.STATUS_IN_PROGRESS
        
        # In a real implementation, we would extract the task ID from the message
        # For now, this is just a placeholder
        
        return {
            "task_id": None,  # This should be extracted from the message
            "status": status
        }
    
    def get_task_summary(self, user_id):
        """
        Get a summary of a user's tasks
        
        Args:
            user_id (str): The user's ID
            
        Returns:
            dict: A summary of the user's tasks
        """
        tasks = Task.get_for_user(user_id)
        
        # Count tasks by status
        pending_count = sum(1 for task in tasks if task.status == Task.STATUS_PENDING)
        done_count = sum(1 for task in tasks if task.status == Task.STATUS_DONE)
        stuck_count = sum(1 for task in tasks if task.status == Task.STATUS_STUCK)
        in_progress_count = sum(1 for task in tasks if task.status == Task.STATUS_IN_PROGRESS)
        
        # Calculate completion rate
        total_tasks = len(tasks)
        completion_rate = 0
        if total_tasks > 0:
            completion_rate = (done_count / total_tasks) * 100
        
        return {
            "total_tasks": total_tasks,
            "pending_count": pending_count,
            "done_count": done_count,
            "stuck_count": stuck_count,
            "in_progress_count": in_progress_count,
            "completion_rate": completion_rate
        }

# Create singleton instance
_task_service = None

def get_task_service():
    """Get the task service instance"""
    global _task_service
    if _task_service is None:
        _task_service = TaskService()
    return _task_service 