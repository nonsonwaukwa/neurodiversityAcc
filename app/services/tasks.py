import random
from datetime import datetime
from app.models.task import Task
from app.models.user import User
from config.settings import Config
from flask import current_app
import logging

logger = logging.getLogger(__name__)

class TaskService:
    """Service for managing tasks and providing ADHD-friendly strategies"""
    
    def __init__(self):
        """Initialize the task service"""
        # ADHD-friendly productivity hacks
        self.adhd_hacks = [
            "Break your task into smaller, more manageable steps.",
            "Use the Pomodoro Technique: 25 minutes of focus, then a 5-minute break.",
            "Remove distractions from your environment before starting.",
            "Create a clear, written checklist for your task.",
            "Set a timer for just 5 minutes - often getting started is the hardest part.",
            "Try body doubling: work alongside someone else (virtually or in person).",
            "Use the 'if-then' planning technique: 'If [situation], then I will [action]'.",
            "Play background music or white noise to help with focus.",
            "Set up visual reminders where you'll notice them.",
            "Reward yourself after completing parts of your task."
        ]
        
        # Self-care tips for rest days
        self.self_care_tips = [
            "Take a short walk outside to get fresh air and sunlight.",
            "Practice deep breathing for 5 minutes.",
            "Stay hydrated - drink a glass of water now.",
            "Stretch your body gently for a few minutes.",
            "Listen to music that makes you feel good.",
            "Write down three things you're grateful for today.",
            "Connect with a friend or loved one, even just for a quick chat.",
            "Take a warm shower or bath.",
            "Eat a nutritious meal or snack.",
            "Spend some time in nature, even if just sitting by a window.",
            "Try a simple meditation or mindfulness exercise.",
            "Give yourself permission to take a short nap.",
            "Read something purely for enjoyment.",
            "Do a small creative activity with no pressure to be 'good' at it.",
            "Declutter one small area of your space."
        ]
    
    def create_task(self, user_id, description):
        """
        Create a new task for a user
        
        Args:
            user_id (str): The user's ID
            description (str): The task description
            
        Returns:
            Task: The created task
        """
        # Ensure the user exists
        user = User.get(user_id)
        if not user:
            raise ValueError(f"User with ID {user_id} not found")
        
        # Create the task
        task = Task.create(user_id, description)
        
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
    
    def get_adhd_hack(self):
        """
        Get a random ADHD-friendly productivity hack
        
        Returns:
            str: An ADHD-friendly strategy
        """
        return random.choice(self.adhd_hacks)
    
    def get_self_care_tip(self):
        """Get a random self-care tip for rest days"""
        return random.choice(self.self_care_tips)
    
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
    
    def create_weekly_tasks(self, user_id, tasks_by_day):
        """
        Create weekly scheduled tasks
        
        Args:
            user_id (str): The user's ID
            tasks_by_day (dict): Dictionary mapping days to task lists
            
        Returns:
            dict: Created tasks by day
        """
        created_tasks = {}
        
        for day_str, task_list in tasks_by_day.items():
            try:
                # Parse day into datetime
                day_date = parse_date(day_str)
                
                day_tasks = []
                for task_desc in task_list:
                    task = Task.create(user_id, task_desc, scheduled_date=day_date)
                    day_tasks.append(task)
                
                created_tasks[day_str] = day_tasks
            
            except Exception as e:
                logger.error(f"Error creating tasks for day {day_str}: {e}")
        
        return created_tasks
    
    def get_tasks_for_day(self, user_id, date):
        """
        Get tasks scheduled for a specific day
        
        Args:
            user_id (str): The user's ID
            date (datetime): The day to get tasks for
            
        Returns:
            list: Tasks for the day
        """
        return Task.get_for_user(user_id, scheduled_date=date)
    
    def get_pending_tasks(self, user_id):
        """
        Get all pending tasks for a user
        
        Args:
            user_id (str): The user's ID
            
        Returns:
            list: Pending tasks
        """
        return Task.get_for_user(user_id, status=Task.STATUS_PENDING)

# Create singleton instance
_task_service = None

def get_task_service():
    """
    Get an instance of the task service
    
    Returns:
        TaskService: The task service instance
    """
    global _task_service
    if _task_service is None:
        _task_service = TaskService()
    return _task_service

def parse_date(date_str):
    """
    Parse a date string into a datetime object
    
    Args:
        date_str (str): Date string in format YYYY-MM-DD
        
    Returns:
        datetime: Parsed date
    """
    if isinstance(date_str, datetime):
        return date_str
    
    # Try different formats
    formats = [
        '%Y-%m-%d',  # 2023-01-01
        '%d/%m/%Y',  # 01/01/2023
        '%m/%d/%Y',  # 01/01/2023
        '%d-%m-%Y',  # 01-01-2023
        '%d %b %Y',  # 01 Jan 2023
        '%d %B %Y'   # 01 January 2023
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    raise ValueError(f"Unable to parse date string: {date_str}")

def send_task_buttons(user, task):
    """
    Send interactive buttons for a task
    
    Args:
        user (User): The user
        task (Task): The task
    """
    from app.services.whatsapp import get_whatsapp_service
    
    whatsapp_service = get_whatsapp_service(user.account_index)
    
    buttons = [
        {
            "id": f"task_{task.task_id}_done",
            "title": "✅ Done"
        },
        {
            "id": f"task_{task.task_id}_progress",
            "title": "🔄 In Progress"
        },
        {
            "id": f"task_{task.task_id}_stuck",
            "title": "❌ Stuck"
        }
    ]
    
    whatsapp_service.send_interactive_message(
        user.user_id,
        f"Task: {task.description}",
        "How are you progressing with this task?",
        buttons
    ) 