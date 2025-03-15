from datetime import datetime
from config.firebase_config import get_db

class CheckIn:
    """CheckIn model representing a user check-in in the system"""
    
    COLLECTION = 'checkins'
    
    # Check-in type constants
    TYPE_DAILY = 'Daily'
    TYPE_WEEKLY = 'Weekly'
    
    def __init__(self, checkin_id, user_id, response, checkin_type=TYPE_DAILY, 
                 sentiment_score=None, created_at=None):
        """
        Initialize a CheckIn object
        
        Args:
            checkin_id (str): Unique identifier
            user_id (str): User ID this check-in belongs to
            response (str): User's emotional state response
            checkin_type (str): Type of check-in (Daily/Weekly)
            sentiment_score (float): NLP sentiment analysis score
            created_at (datetime): Date of check-in
        """
        self.checkin_id = checkin_id
        self.user_id = user_id
        self.response = response
        self.type = checkin_type
        self.sentiment_score = sentiment_score
        self.created_at = created_at or datetime.now()
    
    @classmethod
    def create(cls, user_id, response, checkin_type=TYPE_DAILY, sentiment_score=None):
        """
        Create a new check-in for a user
        
        Args:
            user_id (str): User ID this check-in belongs to
            response (str): User's emotional state response
            checkin_type (str): Type of check-in (Daily/Weekly)
            sentiment_score (float, optional): NLP sentiment analysis score
            
        Returns:
            CheckIn: The created check-in object
        """
        import uuid
        checkin_id = str(uuid.uuid4())
        
        checkin = cls(checkin_id, user_id, response, checkin_type, sentiment_score)
        
        # Convert to dictionary for Firestore
        checkin_data = {
            'checkin_id': checkin.checkin_id,
            'user_id': checkin.user_id,
            'response': checkin.response,
            'type': checkin.type,
            'sentiment_score': checkin.sentiment_score,
            'created_at': checkin.created_at
        }
        
        # Add to Firestore
        get_db().collection(cls.COLLECTION).document(checkin_id).set(checkin_data)
        
        return checkin
    
    @classmethod
    def get(cls, checkin_id):
        """
        Retrieve a check-in from the database
        
        Args:
            checkin_id (str): The check-in's ID
            
        Returns:
            CheckIn: The check-in object if found, None otherwise
        """
        doc = get_db().collection(cls.COLLECTION).document(checkin_id).get()
        
        if not doc.exists:
            return None
        
        checkin_data = doc.to_dict()
        return cls(
            checkin_id=checkin_data.get('checkin_id'),
            user_id=checkin_data.get('user_id'),
            response=checkin_data.get('response'),
            checkin_type=checkin_data.get('type'),
            sentiment_score=checkin_data.get('sentiment_score'),
            created_at=checkin_data.get('created_at')
        )
    
    @classmethod
    def get_for_user(cls, user_id, checkin_type=None, limit=None):
        """
        Retrieve check-ins for a specific user, optionally filtered by type
        
        Args:
            user_id (str): The user's ID
            checkin_type (str, optional): Filter by check-in type
            limit (int, optional): Maximum number of check-ins to retrieve
            
        Returns:
            list: List of CheckIn objects
        """
        query = get_db().collection(cls.COLLECTION).where('user_id', '==', user_id)
        
        if checkin_type:
            query = query.where('type', '==', checkin_type)
        
        # Order by creation date (newest first)
        query = query.order_by('created_at', direction='DESCENDING')
        
        if limit:
            query = query.limit(limit)
        
        docs = query.stream()
        
        checkins = []
        for doc in docs:
            checkin_data = doc.to_dict()
            checkins.append(cls(
                checkin_id=checkin_data.get('checkin_id'),
                user_id=checkin_data.get('user_id'),
                response=checkin_data.get('response'),
                checkin_type=checkin_data.get('type'),
                sentiment_score=checkin_data.get('sentiment_score'),
                created_at=checkin_data.get('created_at')
            ))
        
        return checkins
    
    def update_sentiment_score(self, sentiment_score):
        """
        Update the check-in's sentiment score
        
        Args:
            sentiment_score (float): The sentiment score from AI analysis
        """
        self.sentiment_score = sentiment_score
        
        get_db().collection(self.COLLECTION).document(self.checkin_id).update({
            'sentiment_score': self.sentiment_score
        })
    
    def to_dict(self):
        """Convert the check-in object to a dictionary"""
        return {
            'checkin_id': self.checkin_id,
            'user_id': self.user_id,
            'response': self.response,
            'type': self.type,
            'sentiment_score': self.sentiment_score,
            'created_at': self.created_at
        } 