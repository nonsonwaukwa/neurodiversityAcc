#!/usr/bin/env python3
"""
WhatsApp Test Message Sender

This script sends a direct test message via WhatsApp API to verify that
the account configuration is working properly.
"""

import logging
import sys
from app import create_app
from app.services.whatsapp import get_whatsapp_service

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Default target user ID
TARGET_USER_ID = "2348023672476"

def send_test_message(user_id, account_index=None):
    """
    Send a test message directly via WhatsApp API
    
    Args:
        user_id (str): The user's WhatsApp phone number
        account_index (int, optional): Specific WhatsApp account to use
    """
    try:
        # Get the WhatsApp service
        if account_index is not None:
            whatsapp_service = get_whatsapp_service(account_index)
            logger.info(f"Using explicitly specified account index: {account_index}")
        else:
            # Get the appropriate WhatsApp service for this user
            from app.services.whatsapp import get_whatsapp_service_for_number
            whatsapp_service = get_whatsapp_service_for_number(user_id)
            logger.info(f"Using account index determined by user ID: {whatsapp_service.account_index}")
        
        # Create a test message
        test_message = (
            "🔍 This is a direct test message from the WhatsApp API. "
            "If you received this, your WhatsApp API is correctly configured! "
            "This is part of troubleshooting why follow-up reminders are not being delivered."
        )
        
        # Check connection first
        logger.info("Testing WhatsApp API connection...")
        connection_ok = whatsapp_service.check_connection()
        
        if not connection_ok:
            logger.error("❌ WhatsApp API connection test failed!")
            return False
            
        logger.info("✅ WhatsApp API connection test successful!")
        
        # Send the message
        logger.info(f"Sending test message to user {user_id}")
        response = whatsapp_service.send_message(user_id, test_message)
        
        logger.info(f"WhatsApp API response: {response}")
        logger.info("✅ Test message sent successfully!")
        
        return True
    except Exception as e:
        logger.error(f"❌ Error sending test message: {str(e)}")
        return False

if __name__ == "__main__":
    # Parse command line arguments
    user_id = TARGET_USER_ID
    account_index = None
    
    if len(sys.argv) > 1:
        user_id = sys.argv[1]
    
    if len(sys.argv) > 2:
        try:
            account_index = int(sys.argv[2])
        except ValueError:
            logger.error(f"Invalid account index: {sys.argv[2]}. Must be an integer.")
            sys.exit(1)
    
    # Create Flask app and set up application context
    app = create_app()
    with app.app_context():
        logger.info("="*80)
        logger.info(f"WHATSAPP TEST MESSAGE SENDER")
        logger.info("="*80)
        logger.info(f"Target user ID: {user_id}")
        
        # Send the test message
        success = send_test_message(user_id, account_index)
        
        if success:
            logger.info("="*80)
            logger.info("✅ TEST MESSAGE SENT SUCCESSFULLY")
            logger.info("="*80)
            logger.info("Check your WhatsApp on the target phone to confirm receipt")
        else:
            logger.error("="*80)
            logger.error("❌ FAILED TO SEND TEST MESSAGE")
            logger.error("="*80)
            logger.error("Please check the logs above for details on the error")
            sys.exit(1) 