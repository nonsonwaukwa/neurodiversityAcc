from datetime import datetime, timedelta
import logging
from app.models.user import User
from app.models.checkin import CheckIn
from app.models.task import Task
from firebase_admin import firestore

logger = logging.getLogger(__name__)

class EnhancedAnalyticsService:
    """Enhanced analytics service for tracking additional metrics"""

    @staticmethod
    def update_user_streak(user_id):
        """
        Update user's streak count based on daily activity
        
        Args:
            user_id (str): The user's ID
            
        Returns:
            tuple: (new_streak_count, maintained)
        """
        user = User.get(user_id)
        if not user:
            return 0, False
            
        today = datetime.now().date()
        last_streak_date = user.last_streak_date.date() if user.last_streak_date else None
        
        # Check if streak is maintained
        if last_streak_date and (today - last_streak_date) <= timedelta(days=1):
            # Streak maintained
            if today != last_streak_date:  # Only increment if not already counted today
                user.streak_count += 1
                maintained = True
            else:
                maintained = True
        else:
            # Streak broken
            user.streak_count = 1
            maintained = False
            
        user.last_streak_date = datetime.now()
        
        # Update user in database
        db = firestore.client()
        db.collection('users').document(user_id).update({
            'streak_count': user.streak_count,
            'last_streak_date': user.last_streak_date
        })
        
        return user.streak_count, maintained

    @staticmethod
    def get_streak_statistics():
        """
        Get streak statistics across all users
        
        Returns:
            dict: Streak statistics
        """
        users = User.get_all()
        if not users:
            return {
                'average_streak': 0,
                'max_streak': 0,
                'active_streaks': 0
            }
            
        total_streaks = sum(user.streak_count for user in users)
        max_streak = max(user.streak_count for user in users)
        active_streaks = sum(1 for user in users if user.streak_count > 0)
        
        return {
            'average_streak': total_streaks / len(users),
            'max_streak': max_streak,
            'active_streaks': active_streaks
        }

    @staticmethod
    def log_response_time(user_id, message_sent_time, response_time):
        """
        Log response time for analytics
        
        Args:
            user_id (str): The user's ID
            message_sent_time (datetime): When the message was sent
            response_time (datetime): When the response was received
        """
        time_diff = response_time - message_sent_time
        seconds_diff = time_diff.total_seconds()
        
        db = firestore.client()
        db.collection('response_times').add({
            'user_id': user_id,
            'sent_time': message_sent_time,
            'response_time': response_time,
            'seconds_diff': seconds_diff,
            'created_at': firestore.SERVER_TIMESTAMP
        })

    @staticmethod
    def get_average_response_time(user_id=None, days=7):
        """
        Get average response time for a user or all users
        
        Args:
            user_id (str, optional): Specific user to analyze
            days (int): Number of days to analyze
            
        Returns:
            float: Average response time in seconds
        """
        db = firestore.client()
        start_date = datetime.now() - timedelta(days=days)
        
        query = db.collection('response_times')
        if user_id:
            query = query.where('user_id', '==', user_id)
        
        docs = query.where('created_at', '>=', start_date).stream()
        
        times = [doc.get('seconds_diff') for doc in docs]
        if not times:
            return 0
            
        return sum(times) / len(times)

    @staticmethod
    def track_user_engagement(user_id):
        """
        Track user engagement metrics
        
        Args:
            user_id (str): The user's ID
            
        Returns:
            dict: Engagement metrics
        """
        user = User.get(user_id)
        if not user:
            return None
            
        # Get recent check-ins
        recent_checkins = CheckIn.get_for_user(
            user_id,
            start_date=datetime.now() - timedelta(days=30)
        )
        
        # Get recent tasks
        recent_tasks = Task.get_for_user(
            user_id,
            created_after=datetime.now() - timedelta(days=30)
        )
        
        # Calculate engagement metrics
        total_checkins = len(recent_checkins)
        completed_tasks = sum(1 for task in recent_tasks if task.status == Task.STATUS_DONE)
        days_active = len(set(checkin.created_at.date() for checkin in recent_checkins))
        
        return {
            'total_checkins': total_checkins,
            'completed_tasks': completed_tasks,
            'days_active': days_active,
            'engagement_score': (days_active / 30) * 100  # Percentage of days active
        }

    @staticmethod
    def get_dropout_statistics(days=30):
        """
        Get dropout statistics across all users
        
        Args:
            days (int): Number of days to analyze
            
        Returns:
            dict: Dropout statistics
        """
        users = User.get_all()
        if not users:
            return {
                'dropout_rate': 0,
                'at_risk_users': 0,
                'total_users': 0
            }
            
        cutoff_date = datetime.now() - timedelta(days=days)
        total_users = len(users)
        
        # Count dropped users (no activity in specified days)
        dropped_users = sum(1 for user in users if user.last_active < cutoff_date)
        
        # Count at-risk users (no activity in last 7 days)
        at_risk_cutoff = datetime.now() - timedelta(days=7)
        at_risk_users = sum(1 for user in users 
                          if at_risk_cutoff > user.last_active >= cutoff_date)
        
        return {
            'dropout_rate': (dropped_users / total_users) * 100,
            'at_risk_users': at_risk_users,
            'total_users': total_users
        } 