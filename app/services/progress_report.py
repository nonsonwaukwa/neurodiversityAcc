import logging
from datetime import datetime, timedelta
from app.models.user import User
from app.models.task import Task
from app.models.checkin import CheckIn
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
        in_progress_tasks = [t for t in all_tasks if t.status == Task.STATUS_IN_PROGRESS]
        stuck_tasks = [t for t in all_tasks if t.status == Task.STATUS_STUCK]
        pending_tasks = [t for t in all_tasks if t.status == Task.STATUS_PENDING]
        
        # Get sentiment data
        analytics_service = get_analytics_service()
        sentiment_trend = analytics_service.get_sentiment_trend(user_id, days=7)
        
        # Check if user had tasks and completed some
        has_completed_tasks = len(completed_tasks) > 0
        had_any_tasks = len(all_tasks) > 0
        
        # Based on task history, decide which type of report to generate
        if had_any_tasks and has_completed_tasks:
            # User has completed tasks - generate visual report
            return ProgressReportService._generate_success_report(
                user, completed_tasks, pending_tasks, 
                in_progress_tasks, stuck_tasks, sentiment_trend
            )
        else:
            # User had no tasks or completed none - generate compassionate check-in
            return ProgressReportService._generate_compassion_checkin(user, sentiment_trend)
    
    @staticmethod
    def _generate_success_report(user, completed_tasks, pending_tasks, in_progress_tasks, stuck_tasks, sentiment_trend):
        """
        Generate a success report with metrics
        
        Args:
            user (User): The user object
            completed_tasks (list): Completed tasks
            pending_tasks (list): Pending tasks 
            in_progress_tasks (list): In-progress tasks
            stuck_tasks (list): Stuck tasks
            sentiment_trend (dict): Sentiment trend data
            
        Returns:
            dict: Report data
        """
        # Calculate metrics
        total_tasks = len(completed_tasks) + len(pending_tasks) + len(in_progress_tasks) + len(stuck_tasks)
        completion_rate = len(completed_tasks) / total_tasks if total_tasks > 0 else 0
        
        # Prepare report text
        completed_list = "\n".join([f"✅ {task.description}" for task in completed_tasks[:5]])
        if len(completed_tasks) > 5:
            completed_list += f"\n...and {len(completed_tasks) - 5} more"
        
        # Create report message
        if completion_rate >= 0.7:  # High completion
            praise = "Amazing work this week! You completed most of your tasks."
        elif completion_rate >= 0.4:  # Moderate completion
            praise = "Good progress this week! You're moving forward."
        else:  # Lower completion
            praise = "You made progress this week. Every completed task matters!"
            
        # Add sentiment acknowledgment
        if sentiment_trend["trend"] == "improving":
            mood_note = "I've noticed your mood improving this week. That's wonderful!"
        elif sentiment_trend["trend"] == "declining":
            mood_note = "This week may have had its challenges emotionally. Remember to take care of yourself."
        elif sentiment_trend["trend"] == "positive":
            mood_note = "You've maintained a positive outlook this week. Great job!"
        else:
            mood_note = ""
        
        # Create a text-based visualization of completion rate
        progress_bar = ProgressReportService._create_text_progress_bar(completion_rate)
        
        message = (
            f"📊 *Your Weekly Progress Report*\n\n"
            f"{praise}\n\n"
            f"*Completed tasks:* {len(completed_tasks)}/{total_tasks}\n"
            f"{progress_bar}\n"
            f"*In progress:* {len(in_progress_tasks)}\n"
            f"*Tasks you completed:*\n{completed_list}\n\n"
        )
        
        if mood_note:
            message += f"{mood_note}\n\n"
            
        message += (
            f"What's one thing you're proud of accomplishing this week? "
            f"It doesn't have to be from your task list!"
        )
        
        return {
            "type": "success",
            "message": message,
            "completion_rate": completion_rate,
            "total_tasks": total_tasks,
            "completed_tasks": len(completed_tasks)
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
        Process a user's reflection on a small win
        
        Args:
            user (User): The user object
            reflection_text (str): The user's reflection text
            
        Returns:
            str: Response message
        """
        # Store the reflection
        # We could add a Reflection model in the future, but for now we'll just log it
        logger.info(f"WIN_REFLECTION: User {user.user_id} reflected: {reflection_text}")
        
        # Generate appropriate response
        if len(reflection_text.split()) > 15:  # Longer reflection
            response = (
                f"Thank you for sharing that, {user.name}. It's wonderful to hear about the positive moments "
                f"in your week, no matter how small they might seem. Those small wins and moments of joy "
                f"are important parts of your journey.\n\n"
                f"I'll check in again next week, and remember - progress isn't always linear, "
                f"and every small step counts."
            )
        else:  # Shorter reflection
            response = (
                f"Thank you for sharing that win, {user.name}. Even small positive moments matter! "
                f"I hope the coming week brings more moments like this."
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