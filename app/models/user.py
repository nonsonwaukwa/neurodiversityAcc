from datetime import datetime
from config.firebase_config import get_db

class User:
    """User model representing a user in the system"""
    
    COLLECTION = 'users'
    
    def __init__(self, user_id, name, user_type='Human', account_index=0, created_at=None, last_active=None, sentiment_scores=None):
        """
        Initialize a User object
        
        Args:
            user_id (str): Unique identifier (WhatsApp number)
            name (str): User's name
            user_type (str): 'AI' or 'Human'
            account_index (int): Index of the Meta account the user belongs to (0 or 1)
            created_at (datetime): Date/time user was added
            last_active (datetime): Last time user interacted
            sentiment_scores (list): List of sentiment scores
        """
        self.user_id = user_id
        self.name = name
        self.type = user_type
        self.account_index = account_index
        self.created_at = created_at or datetime.now()
        self.last_active = last_active or datetime.now()
        self.sentiment_scores = sentiment_scores or []
    
    @classmethod
    def create(cls, user_id, name, user_type='Human', account_index=0):
        """
        Create a new user in the database
        
        Args:
            user_id (str): Unique identifier (WhatsApp number)
            name (str): User's name
            user_type (str): 'AI' or 'Human'
            account_index (int): Index of the Meta account the user belongs to (0 or 1)
            
        Returns:
            User: The created user object
        """
        user = cls(user_id, name, user_type, account_index)
        
        # Convert to dictionary for Firestore
        user_data = {
            'user_id': user.user_id,
            'name': user.name,
            'type': user.type,
            'account_index': user.account_index,
            'created_at': user.created_at,
            'last_active': user.last_active,
            'sentiment_scores': user.sentiment_scores
        }
        
        # Add to Firestore
        get_db().collection(cls.COLLECTION).document(user_id).set(user_data)
        
        return user
    
    @classmethod
    def get(cls, user_id):
        """
        Retrieve a user from the database
        
        Args:
            user_id (str): The user's ID
            
        Returns:
            User: The user object if found, None otherwise
        """
        doc = get_db().collection(cls.COLLECTION).document(user_id).get()
        
        if not doc.exists:
            return None
        
        user_data = doc.to_dict()
        return cls(
            user_id=user_data.get('user_id'),
            name=user_data.get('name'),
            user_type=user_data.get('type'),
            account_index=user_data.get('account_index', 0),
            created_at=user_data.get('created_at'),
            last_active=user_data.get('last_active'),
            sentiment_scores=user_data.get('sentiment_scores', [])
        )
    
    @classmethod
    def get_all(cls, user_type=None, account_index=None):
        """
        Retrieve all users from the database, optionally filtered by type and account
        
        Args:
            user_type (str, optional): Filter by user type ('AI' or 'Human')
            account_index (int, optional): Filter by account index (0 or 1)
            
        Returns:
            list: List of User objects
        """
        query = get_db().collection(cls.COLLECTION)
        
        if user_type:
            query = query.where('type', '==', user_type)
        
        if account_index is not None:
            query = query.where('account_index', '==', account_index)
        
        docs = query.stream()
        
        users = []
        for doc in docs:
            user_data = doc.to_dict()
            users.append(cls(
                user_id=user_data.get('user_id'),
                name=user_data.get('name'),
                user_type=user_data.get('type'),
                account_index=user_data.get('account_index', 0),
                created_at=user_data.get('created_at'),
                last_active=user_data.get('last_active'),
                sentiment_scores=user_data.get('sentiment_scores', [])
            ))
        
        return users
    
    def update_last_active(self):
        """Update the user's last active timestamp"""
        self.last_active = datetime.now()
        get_db().collection(self.COLLECTION).document(self.user_id).update({
            'last_active': self.last_active
        })
    
    def add_sentiment_score(self, score, timestamp=None):
        """
        Add a sentiment score to the user's history
        
        Args:
            score (float): The sentiment score
            timestamp (datetime, optional): Time of the score
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        sentiment_entry = {
            'score': score,
            'timestamp': timestamp
        }
        
        self.sentiment_scores.append(sentiment_entry)
        
        get_db().collection(self.COLLECTION).document(self.user_id).update({
            'sentiment_scores': self.sentiment_scores
        })
    
    def to_dict(self):
        """Convert the user object to a dictionary"""
        return {
            'user_id': self.user_id,
            'name': self.name,
            'type': self.type,
            'account_index': self.account_index,
            'created_at': self.created_at,
            'last_active': self.last_active,
            'sentiment_scores': self.sentiment_scores
        } 