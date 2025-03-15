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
        self.api_url = "https://api.deepseek.com/chat/completions"
        
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
            
            # Prepare the prompt for sentiment analysis
            messages = [
                {
                    "role": "system",
                    "content": "You are a sentiment analysis assistant. Analyze the sentiment of the given text and respond with a single number between -1 (most negative) and 1 (most positive). Only respond with the number, no other text."
                },
                {
                    "role": "user",
                    "content": text
                }
            ]
            
            payload = {
                "model": "deepseek-chat",
                "messages": messages,
                "temperature": 0.1,  # Low temperature for consistent results
                "stream": False
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
                sentiment_text = result['choices'][0]['message']['content'].strip()
                
                try:
                    # Convert the response to a float
                    sentiment_score = float(sentiment_text)
                    # Ensure the score is between -1 and 1
                    return max(-1, min(1, sentiment_score))
                except (ValueError, TypeError):
                    print(f"Error parsing sentiment score: {sentiment_text}")
                    return self._mock_analyze(text)
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