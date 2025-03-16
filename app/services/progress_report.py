import logging
from datetime import datetime, timedelta
from app.models.user import User
from app.models.task import Task
from app.models.checkin import CheckIn
from app.models.user_insight import UserInsight
from app.services.whatsapp import get_whatsapp_service
from app.services.analytics import get_analytics_service
import os

logger = logging.getLogger(__name__)

class ProgressReportService:
    """Service for generating progress reports and compassionate check-ins"""
    
    @staticmethod
    def generate_weekly_report(user_id):
        """
        Generate a weekly progress report for a user
        
        Args:
            user_id (str): The user's ID
            
        Returns:
            dict: Report data 
        """
        # Get user data
        user = User.get(user_id)
        if not user:
            logger.error(f"User {user_id} not found for progress report")
            return None
        
        # Get date range for this week
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        # Get tasks for the week
        all_tasks = Task.get_for_user(
            user_id,
            created_after=start_date,
            created_before=end_date
        )
        
        # Count tasks by status
        completed_tasks = [t for t in all_tasks if t.status == Task.STATUS_DONE]
        
        # Get sentiment data
        analytics_service = get_analytics_service()
        sentiment_trend = analytics_service.get_sentiment_trend(user_id, days=7)
        
        # Check if user had tasks and completed some
        has_completed_tasks = len(completed_tasks) > 0
        
        # Based on task history, decide which type of report to generate
        if has_completed_tasks:
            # User has completed tasks - generate celebration report
            return ProgressReportService._generate_success_report(
                user, completed_tasks, sentiment_trend
            )
        else:
            # User had no completed tasks - generate compassionate check-in
            return ProgressReportService._generate_compassion_checkin(user, sentiment_trend)
    
    @staticmethod
    def _generate_success_report(user, completed_tasks, sentiment_trend):
        """
        Generate a success report focusing only on achievements
        
        Args:
            user (User): The user object
            completed_tasks (list): Completed tasks
            sentiment_trend (dict): Sentiment trend data
            
        Returns:
            dict: Report data
        """
        # Prepare completed tasks list
        completed_list = "\n".join([f"✅ {task.description}" for task in completed_tasks[:5]])
        if len(completed_tasks) > 5:
            completed_list += f"\n...and {len(completed_tasks) - 5} more"
        
        # Create celebration message
        if len(completed_tasks) >= 5:
            praise = "Amazing work this week! You completed several tasks and should be proud of yourself."
        elif len(completed_tasks) >= 3:
            praise = "Great job this week! You made meaningful progress on your goals."
        else:
            praise = "Well done! Each task you completed this week is a real achievement."
            
        # Add sentiment acknowledgment if positive
        mood_note = ""
        if sentiment_trend["trend"] == "improving":
            mood_note = "I've noticed your mood improving this week. That's wonderful!"
        elif sentiment_trend["trend"] == "positive":
            mood_note = "You've maintained a positive outlook this week. Great job!"
        
        message = (
            f"🎉 *Your Weekly Celebration*\n\n"
            f"{praise}\n\n"
            f"*Your achievements this week:*\n{completed_list}\n\n"
        )
        
        if mood_note:
            message += f"{mood_note}\n\n"
            
        message += (
            f"What's one strategy or 'hack' that worked well for you this week? "
            f"Your insight might help your future self when things get challenging!"
        )
        
        return {
            "type": "success",
            "message": message,
            "completed_tasks_count": len(completed_tasks)
        }
    
    @staticmethod
    def _create_text_progress_bar(completion_rate, length=10):
        """
        Create a text-based progress bar
        
        Args:
            completion_rate (float): Rate of completion (0.0-1.0)
            length (int): Length of the progress bar
            
        Returns:
            str: A text progress bar
        """
        filled = int(completion_rate * length)
        bar = "▓" * filled + "░" * (length - filled)
        return f"[{bar}] {int(completion_rate * 100)}%"
    
    @staticmethod
    def _generate_compassion_checkin(user, sentiment_trend):
        """
        Generate a compassionate check-in for users who didn't complete tasks
        
        Args:
            user (User): The user object
            sentiment_trend (dict): Sentiment trend data
            
        Returns:
            dict: Report data
        """
        # Base message with compassion
        message = (
            f"*A Moment for Self-Compassion*\n\n"
            f"This week may have been tough, and that's okay. Your effort still matters, "
            f"even when it's not visible in completed tasks.\n\n"
        )
        
        # Add sentiment-specific acknowledgment
        if sentiment_trend["trend"] == "declining":
            message += (
                f"I've noticed you've been feeling a bit down this week. Remember that "
                f"difficult periods are a natural part of life's rhythm, and they do pass.\n\n"
            )
        
        # Invitation for reflection
        message += (
            f"Would you like to reflect on one small thing that felt good this week? "
            f"It could be anything at all - even something tiny like enjoying a cup of tea "
            f"or taking a deep breath when you needed it.\n\n"
            f"You can reply with text or send a voice note - whatever feels easier."
        )
        
        return {
            "type": "compassion",
            "message": message,
            "sentiment_trend": sentiment_trend["trend"]
        }
    
    @staticmethod
    def process_win_reflection(user, reflection_text):
        """
        Process a user's reflection on a small win or successful strategy
        
        Args:
            user (User): The user object
            reflection_text (str): The user's reflection text
            
        Returns:
            str: Response message
        """
        # Store the reflection as an insight, not just a log
        logger.info(f"WIN_REFLECTION: User {user.user_id} reflected: {reflection_text}")
        
        # Identify potential tags based on content
        tags = []
        
        # Check for common strategy categories
        if any(keyword in reflection_text.lower() for keyword in ['break', 'chunking', 'smaller', 'piece']):
            tags.append('task-chunking')
        
        if any(keyword in reflection_text.lower() for keyword in ['timer', 'pomodoro', 'minutes', '25 min']):
            tags.append('time-management')
            
        if any(keyword in reflection_text.lower() for keyword in ['reward', 'treat', 'celebrate']):
            tags.append('rewards')
            
        if any(keyword in reflection_text.lower() for keyword in ['body double', 'friend', 'together', 'alongside']):
            tags.append('body-doubling')
            
        if any(keyword in reflection_text.lower() for keyword in ['morning', 'afternoon', 'evening', 'time of day']):
            tags.append('time-of-day')
            
        if any(keyword in reflection_text.lower() for keyword in ['focus', 'concentration', 'distraction', 'quiet']):
            tags.append('focus-environment')
        
        # Store as a strategy insight
        UserInsight.create(
            user_id=user.user_id,
            content=reflection_text,
            insight_type=UserInsight.TYPE_STRATEGY,
            source='weekly-reflection',
            effectiveness=None,  # Will be determined later based on usage
            tags=tags
        )
        
        # Generate appropriate response
        if len(reflection_text.split()) > 15:  # Longer reflection
            response = (
                f"Thank you for sharing that, {user.name}! The strategy you described is "
                f"really insightful. These personal 'hacks' are often the most valuable tools "
                f"we develop on our journey. I'll remember what worked for you this week and "
                f"may suggest it in the future when you face similar challenges.\n\n"
                f"I look forward to celebrating more of your achievements next week!"
            )
        else:  # Shorter reflection
            response = (
                f"Thanks for sharing what worked for you, {user.name}! Finding strategies that "
                f"help us navigate challenges is so valuable. I've noted this strategy and may "
                f"remind you of it in the future. I hope next week brings more "
                f"moments of success for you!"
            )
            
        return response

# Create singleton instance
_progress_service = None

def get_progress_service():
    """
    Get an instance of the progress report service
    
    Returns:
        ProgressReportService: The progress report service instance
    """
    global _progress_service
    if _progress_service is None:
        _progress_service = ProgressReportService()
    return _progress_service 