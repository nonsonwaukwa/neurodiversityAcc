import logging
from firebase_admin import firestore
from config.firebase_config import get_db

logger = logging.getLogger(__name__)

def is_duplicate_message(message_id):
    """
    Check if a message has been processed before
    
    Args:
        message_id (str): The message ID to check
        
    Returns:
        bool: Whether the message has been processed before
    """
    try:
        db = get_db()
        doc = db.collection('processed_messages').document(message_id).get()
        return doc.exists
    except Exception as e:
        logger.error(f"Error checking duplicate message: {e}")
        return False

def record_message(message_id):
    """
    Record a message as processed
    
    Args:
        message_id (str): The message ID to record
    """
    try:
        db = get_db()
        db.collection('processed_messages').document(message_id).set({
            'timestamp': firestore.SERVER_TIMESTAMP
        })
    except Exception as e:
        logger.error(f"Error recording message: {e}") 