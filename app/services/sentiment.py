import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer
import random
import os

class SentimentAnalysisService:
    """Service for analyzing sentiment of user messages using DeepSeek or transformers model"""
    
    def __init__(self):
        """Initialize the sentiment analysis service"""
        self.model = None
        self.tokenizer = None
        self._load_model()
    
    def _load_model(self):
        """Load the sentiment analysis model"""
        try:
            # Try to use a pre-trained model for sentiment analysis
            # For simplicity, we're using a basic sentiment model from Hugging Face
            model_name = "distilbert-base-uncased-finetuned-sst-2-english"
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
            print("Sentiment analysis model loaded successfully")
        except Exception as e:
            print(f"Error loading sentiment analysis model: {e}")
            print("Using mock sentiment analysis for development")
            self.model = None
            self.tokenizer = None
    
    def analyze(self, text):
        """
        Analyze the sentiment of a text
        
        Args:
            text (str): The text to analyze
            
        Returns:
            float: A sentiment score between -1 (negative) and 1 (positive)
        """
        if self.model is None or self.tokenizer is None:
            # If model loading failed, use mock analysis
            return self._mock_analyze(text)
        
        try:
            # Tokenize and prepare for model
            inputs = self.tokenizer(text, return_tensors="pt", truncation=True, padding=True)
            
            # Get model outputs
            with torch.no_grad():
                outputs = self.model(**inputs)
            
            # Convert logits to probabilities
            probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
            
            # Get positive probability (assuming binary classification: [neg, pos])
            positive_prob = probs[0][1].item()
            
            # Convert to -1 to 1 scale
            sentiment_score = (positive_prob * 2) - 1
            
            return sentiment_score
        
        except Exception as e:
            print(f"Error during sentiment analysis: {e}")
            return self._mock_analyze(text)
    
    def _mock_analyze(self, text):
        """
        Mock sentiment analysis for development or when the model is unavailable
        
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
        text_lower = text.lower()
        
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