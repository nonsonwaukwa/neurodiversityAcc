import logging
from app.services.sentiment import analyze_sentiment
from app.models.user import User

logger = logging.getLogger(__name__)

class NLPService:
    """Natural Language Processing service for analyzing messages"""
    
    def __init__(self):
        """Initialize the NLP service"""
        self.initialized = True
    
    def analyze_message(self, message, user_id=None):
        """
        Analyze a message for intents, entities, and sentiment
        
        Args:
            message (str): The message to analyze
            user_id (str, optional): The user's ID for personalized analysis
            
        Returns:
            dict: Analysis results
        """
        results = {
            'sentiment': None,
            'intents': [],
            'entities': []
        }
        
        try:
            # Analyze sentiment
            sentiment_score = analyze_sentiment(message)
            results['sentiment'] = sentiment_score
            
            # Extract basic intents
            intents = self._detect_intents(message.lower())
            results['intents'] = intents
            
            # Extract entities
            entities = self._extract_entities(message)
            results['entities'] = entities
            
            # Personalize if user_id provided
            if user_id:
                user = User.get(user_id)
                if user:
                    # Adjust analysis based on user preferences or history
                    # This is a placeholder for more sophisticated personalization
                    pass
                    
        except Exception as e:
            logger.error(f"Error analyzing message: {e}")
        
        return results
    
    def _detect_intents(self, message):
        """
        Detect basic intents from a message
        
        Args:
            message (str): The lowercase message to analyze
            
        Returns:
            list: Detected intents
        """
        intents = []
        
        # Greeting intent
        if any(greeting in message for greeting in ['hello', 'hi', 'hey', 'good morning', 'good afternoon']):
            intents.append('greeting')
            
        # Task intent
        if any(task_word in message for task_word in ['task', 'todo', 'to do', 'work on', 'finish']):
            intents.append('task')
            
        # Help intent
        if any(help_word in message for help_word in ['help', 'stuck', 'struggling', 'difficult']):
            intents.append('help')
            
        # Status update intent
        if any(status_word in message for status_word in ['done', 'completed', 'finished', 'working on']):
            intents.append('status_update')
            
        # Question intent
        if any(question_word in message for question_word in ['what', 'how', 'when', 'where', 'why', '?']):
            intents.append('question')
            
        return intents
    
    def _extract_entities(self, message):
        """
        Extract basic entities from a message
        
        Args:
            message (str): The message to analyze
            
        Returns:
            dict: Extracted entities
        """
        # This is a simplified version. In a real application, this would use
        # a more sophisticated NER model or service
        entities = {}
        
        # Extract dates (very simple approach)
        date_indicators = ['today', 'tomorrow', 'yesterday', 'next week', 'Monday', 'Tuesday', 'Wednesday', 
                         'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        for indicator in date_indicators:
            if indicator.lower() in message.lower():
                if 'date' not in entities:
                    entities['date'] = []
                entities['date'].append(indicator)
        
        return entities

# Singleton instance
_nlp_service = None

def get_nlp_service():
    """
    Get an instance of the NLP service
    
    Returns:
        NLPService: The NLP service instance
    """
    global _nlp_service
    if _nlp_service is None:
        _nlp_service = NLPService()
    return _nlp_service 