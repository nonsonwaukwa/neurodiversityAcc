import os
import json
import logging
from datetime import datetime
from firebase_admin import firestore
from config.firebase_config import get_db

# Set up logger
logger = logging.getLogger(__name__)

class VoiceTranscriptionMonitor:
    """Tool to monitor voice transcription accuracy and collect data for improvements"""
    
    def __init__(self):
        """Initialize the monitor"""
        self.db = get_db()
        self.collection = self.db.collection('voice_transcription_logs')
    
    def log_transcription(self, user_id, transcription, confidence=None, success=True):
        """
        Log a transcription event
        
        Args:
            user_id (str): The user's ID
            transcription (str): The transcribed text
            confidence (float, optional): The confidence score if available
            success (bool): Whether the transcription was successful
        """
        try:
            log_data = {
                'user_id': user_id,
                'transcription': transcription,
                'confidence': confidence,
                'success': success,
                'timestamp': firestore.SERVER_TIMESTAMP,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'word_count': len(transcription.split()) if transcription else 0
            }
            
            # Add to database
            self.collection.add(log_data)
            logger.info(f"Logged transcription for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error logging transcription: {e}")
    
    def log_user_feedback(self, user_id, transcription, feedback, original_message_id=None):
        """
        Log user feedback about a transcription
        
        Args:
            user_id (str): The user's ID
            transcription (str): The transcribed text
            feedback (str): The feedback ('accurate', 'inaccurate', 'partially_accurate')
            original_message_id (str, optional): The ID of the original message
        """
        try:
            feedback_data = {
                'user_id': user_id,
                'transcription': transcription,
                'feedback': feedback,
                'original_message_id': original_message_id,
                'timestamp': firestore.SERVER_TIMESTAMP
            }
            
            # Add to database
            self.db.collection('voice_transcription_feedback').add(feedback_data)
            logger.info(f"Logged user feedback for transcription from user {user_id}")
            
        except Exception as e:
            logger.error(f"Error logging user feedback: {e}")
    
    def get_accuracy_stats(self, days=30):
        """
        Get accuracy statistics for the past X days
        
        Args:
            days (int): Number of days to look back
            
        Returns:
            dict: Statistics about transcription accuracy
        """
        try:
            # Calculate the date X days ago
            from datetime import datetime, timedelta
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            
            # Query logs from the past X days
            query = self.collection.where('date', '>=', start_date)
            results = query.stream()
            
            # Analyze the results
            total_count = 0
            success_count = 0
            avg_word_count = 0
            confidence_scores = []
            
            for doc in results:
                data = doc.to_dict()
                total_count += 1
                if data.get('success', False):
                    success_count += 1
                avg_word_count += data.get('word_count', 0)
                if data.get('confidence') is not None:
                    confidence_scores.append(data.get('confidence'))
            
            # Calculate statistics
            success_rate = (success_count / total_count) * 100 if total_count > 0 else 0
            avg_word_count = avg_word_count / total_count if total_count > 0 else 0
            avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
            
            return {
                'total_transcriptions': total_count,
                'success_rate': success_rate,
                'avg_word_count': avg_word_count,
                'avg_confidence': avg_confidence,
                'days_analyzed': days
            }
            
        except Exception as e:
            logger.error(f"Error getting accuracy stats: {e}")
            return None

# Create singleton instance
_voice_monitor = None

def get_voice_monitor():
    """
    Get the voice transcription monitor instance
    
    Returns:
        VoiceTranscriptionMonitor: The monitor instance
    """
    global _voice_monitor
    if _voice_monitor is None:
        _voice_monitor = VoiceTranscriptionMonitor()
    return _voice_monitor 