from datetime import datetime
from config.firebase_config import get_db
import logging

logger = logging.getLogger(__name__)

class User:
    """User model for the accountability system"""
    
    def __init__(self, user_id, name, role='user', account_index=0, planning_type='daily',
                 last_active=None, sentiment_history=None, task_needs_followup=None,
                 streak_count=0, last_streak_date=None, current_hack=None):
        """
        Initialize a user
        
        Args:
            user_id (str): The user's WhatsApp number
            name (str): The user's name
            role (str): The user's role (user or admin)
            account_index (int): The Meta account index this user belongs to
            planning_type (str): The user's planning type (weekly or daily)
            last_active (datetime): When the user was last active
            sentiment_history (list): History of sentiment scores
            task_needs_followup (str): Task ID that needs a follow-up (when user is stuck)
            streak_count (int): Current streak of consecutive days with activity
            last_streak_date (datetime): Last date the streak was updated
            current_hack (dict): Current ADHD hack being tried
        """
        self.user_id = user_id
        self.name = name
        self.role = role
        self.account_index = account_index
        self.planning_type = planning_type
        self.last_active = last_active or datetime.now()
        self.sentiment_history = sentiment_history or []
        self.task_needs_followup = task_needs_followup
        self.streak_count = streak_count
        self.last_streak_date = last_streak_date
        self.current_hack = current_hack
    
    def to_dict(self):
        """Convert the user to a dictionary"""
        return {
            'user_id': self.user_id,
            'name': self.name,
            'role': self.role,
            'account_index': self.account_index,
            'planning_type': self.planning_type,
            'last_active': self.last_active,
            'sentiment_history': self.sentiment_history,
            'task_needs_followup': self.task_needs_followup,
            'streak_count': self.streak_count,
            'last_streak_date': self.last_streak_date,
            'current_hack': self.current_hack
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create a user from a dictionary"""
        return cls(
            user_id=data.get('user_id'),
            name=data.get('name'),
            role=data.get('role', 'user'),
            account_index=data.get('account_index', 0),
            planning_type=data.get('planning_type', 'daily'),
            last_active=data.get('last_active'),
            sentiment_history=data.get('sentiment_history', []),
            task_needs_followup=data.get('task_needs_followup'),
            streak_count=data.get('streak_count', 0),
            last_streak_date=data.get('last_streak_date'),
            current_hack=data.get('current_hack')
        )
    
    @classmethod
    def create(cls, user_id, name, role='user', account_index=0, planning_type='daily'):
        """
        Create a new user
        
        Args:
            user_id (str): The user's WhatsApp number
            name (str): The user's name
            role (str): The user's role (user or admin)
            account_index (int): The Meta account index this user belongs to
            planning_type (str): The user's planning type (weekly or daily)
            
        Returns:
            User: The created user
        """
        db = get_db()
        
        # Create user object
        user = cls(
            user_id=user_id,
            name=name,
            role=role,
            account_index=account_index,
            planning_type=planning_type
        )
        
        # Save to database
        db.collection('users').document(user_id).set(user.to_dict())
        
        return user
    
    @classmethod
    def get(cls, user_id):
        """
        Get a user by ID
        
        Args:
            user_id (str): The user's WhatsApp number
            
        Returns:
            User: The user, or None if not found
        """
        db = get_db()
        doc = db.collection('users').document(user_id).get()
        
        if doc.exists:
            return cls.from_dict(doc.to_dict())
        
        return None
    
    @classmethod
    def get_all(cls):
        """
        Get all users
        
        Returns:
            list: List of users
        """
        db = get_db()
        users = []
        
        for doc in db.collection('users').stream():
            users.append(cls.from_dict(doc.to_dict()))
        
        return users
    
    def update(self):
        """Update the user in the database"""
        db = get_db()
        db.collection('users').document(self.user_id).update(self.to_dict())
    
    def update_last_active(self):
        """Update the user's last active timestamp"""
        self.last_active = datetime.now()
        self.update()
    
    def add_sentiment_score(self, score):
        """
        Add a sentiment score to the user's history
        
        Args:
            score (float): The sentiment score
        """
        if score is not None:
            self.sentiment_history.append({
                'score': score,
                'timestamp': datetime.now()
            })
            
            # Keep only the last 10 scores
            if len(self.sentiment_history) > 10:
                self.sentiment_history = self.sentiment_history[-10:]
            
            self.update()
    
    def update_planning_type(self, planning_type):
        """
        Update the user's planning type
        
        Args:
            planning_type (str): The new planning type (weekly or daily)
        """
        self.planning_type = planning_type
        self.update()
        
    def get_average_sentiment(self, days=7):
        """
        Get the user's average sentiment over the past days
        
        Args:
            days (int): Number of days to look back
            
        Returns:
            float: Average sentiment, or None if no data
        """
        if not self.sentiment_history:
            return None
        
        # Filter by recency
        cutoff = datetime.now() - datetime.timedelta(days=days)
        recent_scores = [item['score'] for item in self.sentiment_history 
                        if item['timestamp'] > cutoff]
        
        if not recent_scores:
            return None
        
        return sum(recent_scores) / len(recent_scores)
    
    def clear_current_hack(self):
        """Clear the current hack being tried"""
        self.current_hack = None
        self.update()
    
    def set_current_hack(self, task_id, hack):
        """
        Set the current hack being tried
        
        Args:
            task_id (str): The task ID
            hack (str): The hack being tried
        """
        self.current_hack = {
            'task_id': task_id,
            'hack': hack,
            'attempts': [hack]
        }
        self.update()
    
    def add_hack_attempt(self, hack):
        """
        Add a hack to the attempts list
        
        Args:
            hack (str): The hack being tried
        """
        if self.current_hack:
            if 'attempts' not in self.current_hack:
                self.current_hack['attempts'] = []
            self.current_hack['attempts'].append(hack)
            self.current_hack['hack'] = hack
            self.update()

    @classmethod
    def get_or_create(cls, user_id, name=None):
        """
        Get a user by ID or create if not exists
        
        Args:
            user_id (str): The user's WhatsApp number
            name (str): The user's name (optional, used only if creating)
            
        Returns:
            User: The existing or newly created user
        """
        user = cls.get(user_id)
        if user:
            return user
            
        # Create new user if not found
        return cls.create(
            user_id=user_id,
            name=name or f"User {user_id[-4:]}"  # Use last 4 digits if no name
        ) 