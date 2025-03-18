from datetime import datetime, timedelta
import logging
from collections import Counter
from app.models.user import User
from app.models.checkin import CheckIn
from app.models.task import Task
from firebase_admin import firestore

logger = logging.getLogger(__name__)

class ConversationAnalyticsService:
    """Service for analyzing conversation topics and themes"""

    TASK_CATEGORIES = [
        'work', 'study', 'health', 'self-care', 'household', 
        'social', 'creative', 'exercise', 'mental_health', 'routine'
    ]

    STRUGGLE_THEMES = [
        'focus', 'procrastination', 'overwhelm', 'time_management',
        'motivation', 'anxiety', 'organization', 'energy', 'sleep',
        'social_interaction', 'executive_function', 'emotional_regulation'
    ]

    @staticmethod
    def analyze_task_themes(task_description):
        """
        Analyze a task description for common themes
        
        Args:
            task_description (str): The task description to analyze
            
        Returns:
            list: Identified themes
        """
        themes = []
        description_lower = task_description.lower()
        
        # Work/Study related
        if any(word in description_lower for word in ['work', 'project', 'meeting', 'email', 'study', 'homework', 'assignment']):
            themes.append('work')
            
        # Health/Self-care
        if any(word in description_lower for word in ['doctor', 'appointment', 'medication', 'self-care', 'therapy', 'rest']):
            themes.append('health')
            
        # Exercise/Physical activity
        if any(word in description_lower for word in ['exercise', 'workout', 'gym', 'walk', 'run', 'yoga']):
            themes.append('exercise')
            
        # Household
        if any(word in description_lower for word in ['clean', 'laundry', 'dishes', 'grocery', 'cook', 'organize']):
            themes.append('household')
            
        # Social
        if any(word in description_lower for word in ['call', 'meet', 'friend', 'family', 'social']):
            themes.append('social')
            
        # Mental Health
        if any(word in description_lower for word in ['meditate', 'journal', 'therapy', 'mindfulness', 'mental health']):
            themes.append('mental_health')
            
        # Routine
        if any(word in description_lower for word in ['morning', 'evening', 'routine', 'daily', 'regular']):
            themes.append('routine')
            
        return themes

    @staticmethod
    def analyze_struggle_themes(message_text):
        """
        Analyze a message for common struggle themes
        
        Args:
            message_text (str): The message to analyze
            
        Returns:
            list: Identified struggle themes
        """
        themes = []
        text_lower = message_text.lower()
        
        # Focus/Attention
        if any(word in text_lower for word in ['focus', 'concentrate', 'distract', 'attention']):
            themes.append('focus')
            
        # Procrastination
        if any(word in text_lower for word in ['procrastinate', 'putting off', 'avoid', 'later']):
            themes.append('procrastination')
            
        # Overwhelm
        if any(word in text_lower for word in ['overwhelm', 'too much', 'stress', 'cant handle']):
            themes.append('overwhelm')
            
        # Time Management
        if any(word in text_lower for word in ['time', 'late', 'deadline', 'schedule']):
            themes.append('time_management')
            
        # Motivation
        if any(word in text_lower for word in ['motivat', 'cant start', 'stuck', 'hard to begin']):
            themes.append('motivation')
            
        # Anxiety
        if any(word in text_lower for word in ['anxi', 'worry', 'stress', 'nervous']):
            themes.append('anxiety')
            
        # Executive Function
        if any(word in text_lower for word in ['organize', 'plan', 'decide', 'start', 'initiate']):
            themes.append('executive_function')
            
        # Emotional Regulation
        if any(word in text_lower for word in ['emotion', 'feel', 'mood', 'overwhelm']):
            themes.append('emotional_regulation')
            
        return themes

    @staticmethod
    def log_conversation_themes(user_id, message_text, message_type='checkin'):
        """
        Log themes from a conversation message
        
        Args:
            user_id (str): The user's ID
            message_text (str): The message content
            message_type (str): Type of message (checkin, task, etc.)
        """
        # Analyze themes
        struggle_themes = ConversationAnalyticsService.analyze_struggle_themes(message_text)
        
        if message_type == 'task':
            task_themes = ConversationAnalyticsService.analyze_task_themes(message_text)
        else:
            task_themes = []
        
        # Store in database
        db = firestore.client()
        db.collection('conversation_themes').add({
            'user_id': user_id,
            'message_text': message_text,
            'message_type': message_type,
            'struggle_themes': struggle_themes,
            'task_themes': task_themes,
            'created_at': firestore.SERVER_TIMESTAMP
        })

    @staticmethod
    def get_user_theme_statistics(user_id, days=30):
        """
        Get theme statistics for a specific user
        
        Args:
            user_id (str): The user's ID
            days (int): Number of days to analyze
            
        Returns:
            dict: Theme statistics
        """
        db = firestore.client()
        start_date = datetime.now() - timedelta(days=days)
        
        # Query themes for this user
        docs = db.collection('conversation_themes')\
                 .where('user_id', '==', user_id)\
                 .where('created_at', '>=', start_date)\
                 .stream()
        
        struggle_themes = []
        task_themes = []
        
        for doc in docs:
            data = doc.to_dict()
            struggle_themes.extend(data.get('struggle_themes', []))
            task_themes.extend(data.get('task_themes', []))
        
        return {
            'common_struggles': Counter(struggle_themes).most_common(),
            'common_tasks': Counter(task_themes).most_common(),
            'total_messages': len(list(docs))
        }

    @staticmethod
    def get_global_theme_statistics(days=30):
        """
        Get theme statistics across all users
        
        Args:
            days (int): Number of days to analyze
            
        Returns:
            dict: Global theme statistics
        """
        db = firestore.client()
        start_date = datetime.now() - timedelta(days=days)
        
        # Query all themes
        docs = db.collection('conversation_themes')\
                 .where('created_at', '>=', start_date)\
                 .stream()
        
        struggle_themes = []
        task_themes = []
        user_themes = {}  # Track themes by user
        
        for doc in docs:
            data = doc.to_dict()
            user_id = data.get('user_id')
            
            # Global counts
            struggle_themes.extend(data.get('struggle_themes', []))
            task_themes.extend(data.get('task_themes', []))
            
            # Per-user tracking
            if user_id not in user_themes:
                user_themes[user_id] = {
                    'struggles': [],
                    'tasks': []
                }
            user_themes[user_id]['struggles'].extend(data.get('struggle_themes', []))
            user_themes[user_id]['tasks'].extend(data.get('task_themes', []))
        
        # Calculate averages per user
        num_users = len(user_themes)
        avg_struggles_per_user = len(struggle_themes) / num_users if num_users > 0 else 0
        avg_tasks_per_user = len(task_themes) / num_users if num_users > 0 else 0
        
        return {
            'global_struggles': Counter(struggle_themes).most_common(),
            'global_tasks': Counter(task_themes).most_common(),
            'total_messages': len(list(docs)),
            'unique_users': num_users,
            'avg_struggles_per_user': avg_struggles_per_user,
            'avg_tasks_per_user': avg_tasks_per_user,
            'theme_distribution': {
                'struggles': {theme: count for theme, count in Counter(struggle_themes).items()},
                'tasks': {theme: count for theme, count in Counter(task_themes).items()}
            }
        } 