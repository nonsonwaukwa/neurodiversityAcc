import os
import json
import requests
import random
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class SentimentAnalysisService:
    """Service for analyzing sentiment of user messages using DeepSeek API"""
    
    def __init__(self):
        """Initialize the sentiment analysis service"""
        self.api_key = os.environ.get('DEEPSEEK_API_KEY')
        self.api_url = "https://api.deepseek.com/v1/sentiment"  # Replace with actual DeepSeek API endpoint
        
        if not self.api_key:
            print("WARNING: DEEPSEEK_API_KEY not found in environment variables!")
            print("Using mock sentiment analysis for development")
    
    def analyze(self, text):
        """
        Analyze the sentiment of a text using DeepSeek API
        
        Args:
            text (str): The text to analyze
            
        Returns:
            float: A sentiment score between -1 (negative) and 1 (positive)
        """
        if not self.api_key or not text:
            return self._mock_analyze(text)
        
        try:
            # Prepare request to DeepSeek API
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "text": text,
                "model": "sentiment-analysis"  # Adjust based on DeepSeek's model naming
            }
            
            # Make API request
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=10
            )
            
            # Check if request was successful
            if response.status_code == 200:
                result = response.json()
                
                # Extract sentiment score from response
                # Note: Adjust based on actual DeepSeek API response format
                sentiment_score = result.get("sentiment_score", 0)
                
                # Ensure score is between -1 and 1
                return max(-1, min(1, sentiment_score))
            else:
                print(f"DeepSeek API error: {response.status_code} - {response.text}")
                return self._mock_analyze(text)
                
        except Exception as e:
            print(f"Error during DeepSeek sentiment analysis: {str(e)}")
            return self._mock_analyze(text)
    
    def _mock_analyze(self, text):
        """
        Mock sentiment analysis for development or when the API is unavailable
        
        Args:
            text (str): The text to analyze
            
        Returns:
            float: A mock sentiment score between -1 (negative) and 1 (positive)
        """
        # Simple keyword-based approach
        positive_words = ["good", "great", "excellent", "happy", "excited", "joy", "wonderful", "fantastic", 
                         "nice", "love", "positive", "amazing", "well", "better", "okay", "fine", "calm"]
        
        negative_words = ["bad", "terrible", "sad", "depressed", "angry", "upset", "awful", "horrible", 
                         "hate", "negative", "stressed", "anxious", "worried", "overwhelmed", "struggling"]
        
        # Convert to lowercase for comparison
        text_lower = text.lower() if text else ""
        
        # Count occurrences of positive and negative words
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        # Calculate score
        if positive_count + negative_count == 0:
            # If no sentiment words found, return a slightly random neutral score
            return random.uniform(-0.1, 0.1)
        
        # Weighted score between -1 and 1
        score = (positive_count - negative_count) / (positive_count + negative_count)
        
        return score

# Create singleton instance
_sentiment_service = None

def get_sentiment_service():
    """Get the sentiment analysis service instance"""
    global _sentiment_service
    if _sentiment_service is None:
        _sentiment_service = SentimentAnalysisService()
    return _sentiment_service 