from datetime import datetime
from config.firebase_config import get_db
import uuid
from firebase_admin import firestore

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
    def create(cls, user_id, response, checkin_type=None, sentiment_score=None):
        """
        Create a new check-in
        
        Args:
            user_id (str): The user's WhatsApp number
            response (str): The check-in response text
            checkin_type (str, optional): The type of check-in (daily/weekly)
            sentiment_score (float, optional): NLP sentiment analysis score
            
        Returns:
            CheckIn: The created check-in
        """
        # Determine if this is a system message or user response
        # System messages are typically questions/prompts, user responses are answers
        is_response = not (
            "How are you feeling" in response or 
            "check in" in response.lower() or
            "Good morning" in response or
            "Hey" in response or
            "tasks would you like" in response
        )
        
        db = get_db()
        
        # Generate a unique ID
        checkin_id = str(uuid.uuid4())
        
        # Create check-in data
        data = {
            'user_id': user_id,
            'response': response,
            'is_response': is_response,
            'created_at': firestore.SERVER_TIMESTAMP
        }
        
        if checkin_type:
            data['checkin_type'] = checkin_type
        
        if sentiment_score is not None:
            data['sentiment_score'] = sentiment_score
        
        # Save to Firestore
        db.collection('checkins').document(checkin_id).set(data)
        
        # Return check-in object
        created_at = datetime.now()  # Temporary until server timestamp is available
        
        return cls(
            checkin_id=checkin_id,
            user_id=user_id,
            response=response,
            checkin_type=checkin_type,
            sentiment_score=sentiment_score,
            created_at=created_at
        )
    
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
    
    @staticmethod
    def get_for_user(user_id, limit=None, checkin_type=None, start_date=None, is_response=None):
        """
        Get check-ins for a specific user
        
        Args:
            user_id (str): The user's ID
            limit (int, optional): Max number of check-ins to retrieve
            checkin_type (str, optional): Filter by check-in type
            start_date (datetime, optional): Get check-ins after this date
            is_response (bool, optional): Filter by whether it's a user response
            
        Returns:
            list: List of check-ins
        """
        db = get_db()
        query = db.collection('checkins').where('user_id', '==', user_id)
        
        # Apply type filter
        if checkin_type:
            query = query.where('checkin_type', '==', checkin_type)
        
        # Apply response filter if specified
        if is_response is not None:
            query = query.where('is_response', '==', is_response)
        
        # Get results ordered by creation time (newest first)
        query = query.order_by('created_at', direction="DESCENDING")
        
        # Apply limit if specified
        if limit:
            query = query.limit(limit)
        
        results = query.stream()
        
        checkins = []
        for doc in results:
            data = doc.to_dict()
            
            # Skip if before start_date
            if start_date and data.get('created_at') and data['created_at'].datetime < start_date:
                continue
            
            checkin_id = doc.id
            user_id = data.get('user_id')
            response = data.get('response')
            checkin_type = data.get('checkin_type')
            sentiment_score = data.get('sentiment_score')
            created_at = data.get('created_at')
            
            # Convert timestamp to datetime
            if created_at:
                created_at = created_at.datetime
            
            checkin = CheckIn(
                checkin_id=checkin_id,
                user_id=user_id,
                response=response,
                checkin_type=checkin_type,
                sentiment_score=sentiment_score,
                created_at=created_at
            )
            checkins.append(checkin)
        
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