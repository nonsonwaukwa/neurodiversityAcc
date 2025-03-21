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
    TYPE_END_OF_DAY = 'EndOfDay'
    
    # Tracking type constants
    TRACKING_TYPE_AI = 'AI'
    TRACKING_TYPE_HUMAN = 'HUMAN'
    
    # Input method constants
    INPUT_METHOD_WHATSAPP = 'WHATSAPP'
    INPUT_METHOD_BACKOFFICE = 'BACKOFFICE'
    
    def __init__(self, checkin_id, user_id, response, checkin_type=TYPE_DAILY, 
                 sentiment_score=None, created_at=None, tracking_type=TRACKING_TYPE_AI,
                 input_method=INPUT_METHOD_WHATSAPP):
        """
        Initialize a CheckIn object
        
        Args:
            checkin_id (str): Unique identifier
            user_id (str): User ID this check-in belongs to
            response (str): User's emotional state response
            checkin_type (str): Type of check-in (Daily/Weekly)
            sentiment_score (float): NLP sentiment analysis score
            created_at (datetime): Date of check-in
            tracking_type (str): Whether check-in is tracked via AI or human input
            input_method (str): How the check-in was created (WhatsApp or back office)
        """
        self.checkin_id = checkin_id
        self.user_id = user_id
        self.response = response
        self.type = checkin_type
        self.sentiment_score = sentiment_score
        self.created_at = created_at or datetime.now()
        self.tracking_type = tracking_type
        self.input_method = input_method
    
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
        # First get by user_id only
        query = db.collection('checkins').where('user_id', '==', user_id)
        
        # Then filter in memory for other conditions
        results = query.stream()
        checkins = []
        
        for doc in results:
            data = doc.to_dict()
            
            # Apply filters in memory
            if checkin_type and data.get('type') != checkin_type:
                continue
                
            if start_date and data.get('created_at') < start_date:
                continue
                
            if is_response is not None:
                is_system_message = data.get('tracking_type') == CheckIn.TRACKING_TYPE_AI
                if is_response and is_system_message:
                    continue
                if not is_response and not is_system_message:
                    continue
            
            checkin = CheckIn(
                checkin_id=doc.id,
                user_id=data.get('user_id'),
                response=data.get('response'),
                checkin_type=data.get('type'),
                sentiment_score=data.get('sentiment_score'),
                created_at=data.get('created_at'),
                tracking_type=data.get('tracking_type', CheckIn.TRACKING_TYPE_AI),
                input_method=data.get('input_method', CheckIn.INPUT_METHOD_WHATSAPP)
            )
            checkins.append(checkin)
        
        # Sort by created_at (newest first)
        checkins.sort(key=lambda x: x.created_at if x.created_at else datetime.min, reverse=True)
        
        # Apply limit
        if limit:
            checkins = checkins[:limit]
            
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
        """Convert the check-in to a dictionary"""
        return {
            'checkin_id': self.checkin_id,
            'user_id': self.user_id,
            'response': self.response,
            'type': self.type,
            'sentiment_score': self.sentiment_score,
            'created_at': self.created_at,
            'tracking_type': self.tracking_type,
            'input_method': self.input_method
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create a CheckIn instance from a dictionary"""
        return cls(
            checkin_id=data.get('checkin_id'),
            user_id=data.get('user_id'),
            response=data.get('response'),
            checkin_type=data.get('type', cls.TYPE_DAILY),
            sentiment_score=data.get('sentiment_score'),
            created_at=data.get('created_at'),
            tracking_type=data.get('tracking_type', cls.TRACKING_TYPE_AI),
            input_method=data.get('input_method', cls.INPUT_METHOD_WHATSAPP)
        ) 