import logging
from datetime import datetime, timedelta
from app.models.user import User
from app.models.checkin import CheckIn
from app.models.task import Task

logger = logging.getLogger(__name__)

class AnalyticsService:
    """Service for tracking user analytics and metrics"""
    
    @staticmethod
    def log_mood_change(user_id, old_sentiment, new_sentiment, context="check-in"):
        """
        Log a significant mood change for analytics
        
        Args:
            user_id (str): The user's ID
            old_sentiment (float): Previous sentiment score
            new_sentiment (float): New sentiment score
            context (str): Context of the mood change
        """
        # Only log significant changes (>0.3 difference)
        if abs(new_sentiment - old_sentiment) < 0.3:
            return
            
        change_direction = "improved" if new_sentiment > old_sentiment else "declined"
        logger.info(f"MOOD_CHANGE: User {user_id} sentiment {change_direction} from {old_sentiment:.2f} to {new_sentiment:.2f} during {context}")
        
        # Here you could store this in a database table specifically for analytics

    @staticmethod
    def log_task_completion(user_id, task_id, task_description, completion_time=None):
        """
        Log a task completion event
        
        Args:
            user_id (str): The user's ID
            task_id (str): The completed task's ID
            task_description (str): Description of the task
            completion_time (datetime): When the task was completed
        """
        if not completion_time:
            completion_time = datetime.now()
            
        logger.info(f"TASK_COMPLETED: User {user_id} completed task '{task_description}' ({task_id})")
        
    @staticmethod
    def get_user_response_rate(user_id, days=7):
        """
        Calculate a user's response rate to check-ins
        
        Args:
            user_id (str): The user's ID
            days (int): Number of days to look back
            
        Returns:
            float: Response rate percentage
        """
        start_date = datetime.now() - timedelta(days=days)
        
        # Get all check-ins sent to user (not responses)
        sent_checkins = CheckIn.get_for_user(
            user_id, 
            start_date=start_date,
            is_response=False
        )
        
        # Get responses from user
        user_responses = CheckIn.get_for_user(
            user_id,
            start_date=start_date,
            is_response=True
        )
        
        if not sent_checkins:
            return 100.0  # No check-ins sent
            
        return (len(user_responses) / len(sent_checkins)) * 100
    
    @staticmethod
    def get_task_completion_rate(user_id, days=7):
        """
        Calculate a user's task completion rate
        
        Args:
            user_id (str): The user's ID
            days (int): Number of days to look back
            
        Returns:
            float: Completion rate percentage
        """
        start_date = datetime.now() - timedelta(days=days)
        
        # Get all tasks created in the time period
        all_tasks = Task.get_for_user(
            user_id,
            created_after=start_date
        )
        
        if not all_tasks:
            return 100.0  # No tasks created
            
        # Count completed tasks
        completed_tasks = [t for t in all_tasks if t.status == Task.STATUS_DONE]
        
        return (len(completed_tasks) / len(all_tasks)) * 100
        
    @staticmethod
    def get_sentiment_trend(user_id, days=14):
        """
        Analyze sentiment trend for a user over time
        
        Args:
            user_id (str): The user's ID
            days (int): Number of days to analyze
            
        Returns:
            dict: Sentiment analysis results
        """
        user = User.get(user_id)
        if not user or not user.sentiment_history:
            return {"trend": "neutral", "average": 0}
            
        # Get sentiment scores in the timeframe
        start_date = datetime.now() - timedelta(days=days)
        recent_scores = [
            score for date, score in user.sentiment_history.items()
            if datetime.fromisoformat(date) >= start_date
        ]
        
        if not recent_scores:
            return {"trend": "neutral", "average": 0}
            
        # Calculate trend
        average = sum(recent_scores) / len(recent_scores)
        
        # Simple trend analysis
        if average > 0.2:
            trend = "positive"
        elif average < -0.2:
            trend = "negative"
        else:
            trend = "neutral"
            
        # Check for improvement or decline
        if len(recent_scores) >= 2:
            first_half = recent_scores[:len(recent_scores)//2]
            second_half = recent_scores[len(recent_scores)//2:]
            
            first_avg = sum(first_half) / len(first_half)
            second_avg = sum(second_half) / len(second_half)
            
            if second_avg - first_avg > 0.2:
                trend = "improving"
            elif first_avg - second_avg > 0.2:
                trend = "declining"
        
        return {
            "trend": trend,
            "average": average,
            "samples": len(recent_scores)
        }

def calculate_metrics(user_ids=None, days=30):
    """
    Calculate various metrics for users
    
    Args:
        user_ids (list): Optional list of user IDs to calculate metrics for
        days (int): Number of days to analyze
        
    Returns:
        dict: Dictionary of metrics
    """
    metrics = {
        'total_users': 0,
        'active_users': 0,
        'total_tasks': 0,
        'completed_tasks': 0,
        'task_completion_rate': 0,
        'avg_sentiment': 0,
        'response_rate': 0
    }
    
    # Get all users or specific users
    users = []
    if user_ids:
        for user_id in user_ids:
            user = User.get(user_id)
            if user:
                users.append(user)
    else:
        users = User.get_all()
    
    if not users:
        return metrics
    
    # Total users
    metrics['total_users'] = len(users)
    
    # Calculate active users (users with activity in the time period)
    start_date = datetime.now() - timedelta(days=days)
    active_users = 0
    total_sentiment = 0
    sentiment_count = 0
    total_response_rate = 0
    response_rate_count = 0
    
    for user in users:
        # Check for recent tasks
        tasks = Task.get_for_user(user.id, created_after=start_date)
        
        if tasks:
            active_users += 1
            
            # Add to task counts
            metrics['total_tasks'] += len(tasks)
            completed_tasks = [t for t in tasks if t.status == Task.STATUS_DONE]
            metrics['completed_tasks'] += len(completed_tasks)
        
        # Get sentiment data
        sentiment_data = AnalyticsService.get_sentiment_trend(user.id, days=days)
        if sentiment_data['samples'] > 0:
            total_sentiment += sentiment_data['average']
            sentiment_count += 1
        
        # Get response rate
        response_rate = AnalyticsService.get_user_response_rate(user.id, days=days)
        if response_rate is not None:
            total_response_rate += response_rate
            response_rate_count += 1
    
    # Calculate aggregated metrics
    metrics['active_users'] = active_users
    
    if metrics['total_tasks'] > 0:
        metrics['task_completion_rate'] = (metrics['completed_tasks'] / metrics['total_tasks']) * 100
    
    if sentiment_count > 0:
        metrics['avg_sentiment'] = total_sentiment / sentiment_count
    
    if response_rate_count > 0:
        metrics['response_rate'] = total_response_rate / response_rate_count
    
    return metrics

# Create singleton instance
_analytics_service = None

def get_analytics_service():
    """
    Get an instance of the analytics service
    
    Returns:
        AnalyticsService: The analytics service instance
    """
    global _analytics_service
    if _analytics_service is None:
        _analytics_service = AnalyticsService()
    return _analytics_service 