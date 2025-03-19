import random
from datetime import datetime
from app.models.task import Task
from app.models.user import User
from app.models.user_insight import UserInsight
from config.settings import Config
from flask import current_app
import logging
import re

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
    
    def get_adhd_hack(self, user_id=None, task_description=None, exclude_hacks=None):
        """
        Get a productivity hack for a user, personalized if possible
        
        Args:
            user_id (str, optional): The user's ID for personalization
            task_description (str, optional): The task description for context
            exclude_hacks (list, optional): List of hacks to exclude
            
        Returns:
            tuple: (str, bool) - (hack, is_personalized)
        """
        # If we don't have user ID or task description, return a generic hack
        if not user_id or not task_description:
            available_hacks = [h for h in self.adhd_hacks if not exclude_hacks or h not in exclude_hacks]
            return random.choice(available_hacks if available_hacks else self.adhd_hacks), False
        
        # Extract keywords from task description
        keywords = self._extract_keywords(task_description)
        
        # Try to get personalized strategies based on what's worked before for this user
        try:
            # Get user's successful strategies
            personalized_strategies = UserInsight.get_strategies_for_task_type(
                user_id, 
                keywords, 
                limit=2
            )
            
            # Filter out excluded hacks
            if exclude_hacks:
                personalized_strategies = [s for s in personalized_strategies if s.content not in exclude_hacks]
            
            # If we found personalized strategies, return one
            if personalized_strategies:
                # Add prefix to make it clear this is based on their past success
                strategy = personalized_strategies[0].content
                return strategy, True
        except Exception as e:
            logger.error(f"Error getting personalized strategies: {e}")
        
        # If no personalized strategies or an error occurred, fall back to general strategies
        available_hacks = [h for h in self.adhd_hacks if not exclude_hacks or h not in exclude_hacks]
        return random.choice(available_hacks if available_hacks else self.adhd_hacks), False
    
    def _extract_keywords(self, text):
        """
        Extract keywords from text for matching strategies
        
        Args:
            text (str): The text to analyze
            
        Returns:
            list: List of keywords
        """
        # Convert to lowercase
        text = text.lower()
        
        # Split into words and remove common stop words
        stop_words = ['a', 'an', 'the', 'and', 'or', 'but', 'to', 'for', 'with', 'in', 'on', 'at', 'by']
        words = [word for word in re.findall(r'\b\w+\b', text) if word not in stop_words and len(word) > 2]
        
        # Check for common ADHD challenge categories
        categories = []
        
        if any(word in text for word in ['focus', 'concentrate', 'attention', 'distract']):
            categories.append('focus')
            
        if any(word in text for word in ['start', 'begin', 'initiate', 'procrastinate']):
            categories.append('initiation')
            
        if any(word in text for word in ['finish', 'complete', 'end']):
            categories.append('completion')
            
        if any(word in text for word in ['boring', 'tedious', 'dull', 'repetitive']):
            categories.append('motivation')
            
        if any(word in text for word in ['deadline', 'due', 'time', 'late']):
            categories.append('time-management')
        
        # Combine specific words and categories
        keywords = words + categories
        return keywords
    
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
    
    def log_task_completion(self, user_id, task_id, success_level=None):
        """
        Log a task completion and collect insights
        
        Args:
            user_id (str): The user's ID
            task_id (str): The task ID
            success_level (int, optional): Rating of how successful the completion was (1-5)
            
        Returns:
            bool: Success status
        """
        try:
            task = Task.get(task_id)
            if not task:
                return False
                
            # Get task details
            task_description = task.description
            
            # Try to detect time of day patterns
            current_hour = datetime.now().hour
            
            time_category = None
            if 5 <= current_hour < 12:
                time_category = 'morning'
            elif 12 <= current_hour < 17:
                time_category = 'afternoon'
            elif 17 <= current_hour < 21:
                time_category = 'evening'
            else:
                time_category = 'night'
                
            # Store time pattern insight
            tags = ['completion-time', time_category]
            UserInsight.create(
                user_id=user_id,
                content=f"Completed task during {time_category} ({current_hour}:00)",
                insight_type=UserInsight.TYPE_TIME_PATTERN,
                task_id=task_id,
                task_description=task_description,
                tags=tags
            )
            
            # Add analytics logging
            analytics_service = get_analytics_service()
            if analytics_service:
                analytics_service.log_task_completion(
                    user_id=user_id,
                    task_id=task_id,
                    task_description=task_description
                )
                
            return True
            
        except Exception as e:
            logger.error(f"Error logging task completion: {e}")
            return False
            
    def log_task_obstacle(self, user_id, task_id, obstacle_description):
        """
        Log an obstacle that prevented task completion
        
        Args:
            user_id (str): The user's ID
            task_id (str): The task ID
            obstacle_description (str): Description of the obstacle
            
        Returns:
            bool: Success status
        """
        try:
            task = Task.get(task_id)
            if not task:
                return False
                
            # Store obstacle insight
            tags = ['obstacle']
            
            # Check for common obstacle types
            if any(word in obstacle_description.lower() for word in ['distract', 'focus', 'attention']):
                tags.append('focus-issue')
                
            if any(word in obstacle_description.lower() for word in ['time', 'forgot', 'late']):
                tags.append('time-management')
                
            if any(word in obstacle_description.lower() for word in ['energy', 'tired', 'exhausted']):
                tags.append('energy-issue')
                
            if any(word in obstacle_description.lower() for word in ['anxiety', 'fear', 'worried']):
                tags.append('anxiety')
                
            if any(word in obstacle_description.lower() for word in ['motivation', 'boring', 'interest']):
                tags.append('motivation')
                
            # Store the obstacle
            UserInsight.create(
                user_id=user_id,
                content=obstacle_description,
                insight_type=UserInsight.TYPE_OBSTACLE,
                task_id=task_id,
                task_description=task.description,
                tags=tags
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error logging task obstacle: {e}")
            return False
            
    def get_personalized_task_suggestions(self, user_id):
        """
        Get personalized task management suggestions based on user patterns
        
        Args:
            user_id (str): The user's ID
            
        Returns:
            dict: Personalized suggestions
        """
        try:
            user = User.get(user_id)
            if not user:
                return {}
                
            # Get user's successful strategies
            strategies = UserInsight.get_for_user(
                user_id,
                insight_type=UserInsight.TYPE_STRATEGY,
                limit=10
            )
            
            # Get completion time patterns
            time_patterns = UserInsight.get_for_user(
                user_id,
                insight_type=UserInsight.TYPE_TIME_PATTERN,
                limit=10
            )
            
            # Analyze time patterns
            morning_count = sum(1 for p in time_patterns if 'morning' in p.tags)
            afternoon_count = sum(1 for p in time_patterns if 'afternoon' in p.tags)
            evening_count = sum(1 for p in time_patterns if 'evening' in p.tags)
            night_count = sum(1 for p in time_patterns if 'night' in p.tags)
            
            total_times = morning_count + afternoon_count + evening_count + night_count
            
            preferred_time = None
            if total_times > 0:
                times = {
                    'morning': morning_count,
                    'afternoon': afternoon_count,
                    'evening': evening_count,
                    'night': night_count
                }
                preferred_time = max(times, key=times.get)
            
            # Get common obstacles
            obstacles = UserInsight.get_for_user(
                user_id,
                insight_type=UserInsight.TYPE_OBSTACLE,
                limit=10
            )
            
            # Analyze obstacles
            obstacle_tags = {}
            for obstacle in obstacles:
                for tag in obstacle.tags:
                    if tag != 'obstacle':  # Skip the generic obstacle tag
                        obstacle_tags[tag] = obstacle_tags.get(tag, 0) + 1
            
            common_obstacle = None
            if obstacle_tags:
                common_obstacle = max(obstacle_tags, key=obstacle_tags.get)
            
            # Build personalized suggestions
            suggestions = {}
            
            # Add preferred time suggestion if available
            if preferred_time:
                suggestions['preferred_time'] = {
                    'time': preferred_time,
                    'message': f"You tend to complete tasks most successfully during the {preferred_time}."
                }
            
            # Add strategy suggestions
            if strategies:
                suggestions['strategies'] = [s.content for s in strategies[:3]]
            
            # Add obstacle awareness
            if common_obstacle:
                suggestions['common_obstacle'] = {
                    'type': common_obstacle,
                    'message': f"You tend to struggle with {common_obstacle.replace('-', ' ')}. Consider planning for this challenge."
                }
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Error getting personalized suggestions: {e}")
            return {}

    def log_successful_strategy(self, user_id, task_id, strategy, task_description):
        """
        Log a strategy that successfully helped a user
        
        Args:
            user_id (str): The user's ID
            task_id (str): The task ID
            strategy (str): The successful strategy
            task_description (str): The task description for context
            
        Returns:
            bool: Success status
        """
        try:
            # Extract task themes/keywords
            keywords = self._extract_keywords(task_description)
            
            # Store the successful strategy
            UserInsight.create(
                user_id=user_id,
                content=strategy,
                insight_type=UserInsight.TYPE_STRATEGY,
                task_id=task_id,
                task_description=task_description,
                tags=['successful-strategy'] + keywords
            )
            
            # Log analytics
            analytics_service = get_analytics_service()
            if analytics_service:
                analytics_service.log_strategy_success(
                    user_id=user_id,
                    task_id=task_id,
                    strategy=strategy,
                    task_description=task_description
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Error logging successful strategy: {e}")
            return False

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
            "title": "✨ Completed"
        },
        {
            "id": f"task_{task.task_id}_progress",
            "title": "🌱 Working on it"
        },
        {
            "id": f"task_{task.task_id}_stuck",
            "title": "💜 Need support"
        }
    ]
    
    whatsapp_service.send_interactive_message(
        user.user_id,
        f"Intention: {task.description}",
        "How are things going with this? No pressure - any progress is valid.",
        buttons
    )

from app.services.analytics import get_analytics_service 