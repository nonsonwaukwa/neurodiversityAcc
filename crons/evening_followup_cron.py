#!/usr/bin/env python3
"""
Evening Follow-up Reminder Cron Script (6:30 PM)

This script triggers the follow-up reminders webhook for users 
who haven't responded to their daily check-ins, 8 hours after the initial check-in.
It's designed to be executed as a standalone cron job on Railway.

Required environment variables:
- APP_URL: The base URL of the deployed application
- CRON_SECRET: Secret token for webhook authentication
"""

import os
import logging
import requests
import json
from datetime import datetime, timezone
from urllib.parse import urljoin
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def trigger_followup_reminders():
    """
    Trigger the follow-up reminders webhook for users who haven't responded to their check-ins.
    """
    app_url = os.environ.get('APP_URL')
    cron_secret = os.environ.get('CRON_SECRET')
    
    if not app_url or not cron_secret:
        logger.error("Missing required environment variables (APP_URL or CRON_SECRET)")
        return False
    
    # Construct webhook URL
    webhook_url = urljoin(app_url, '/api/cron/followup-reminders')
    
    # Prepare headers with authentication
    headers = {
        'Content-Type': 'application/json',
        'X-Cron-Secret': cron_secret
    }
    
    # Prepare payload with timestamp and reminder type
    payload = {
        'timestamp': datetime.now(timezone.UTC).isoformat(),
        'reminder_type': 'evening'  # Indicates this is the evening follow-up
    }
    
    # Make the request
    try:
        logger.info(f"Triggering evening follow-up reminders webhook at {webhook_url}")
        response = requests.post(webhook_url, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            logger.info(f"Evening follow-up reminders webhook triggered successfully: {response.text}")
            return True
        else:
            logger.error(f"Failed to trigger evening follow-up reminders webhook. Status: {response.status_code}, Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Error triggering evening follow-up reminders webhook: {str(e)}")
        return False

if __name__ == "__main__":
    # Skip execution during Railway build process
    if os.environ.get('RAILWAY_STATIC_URL'):
        logger.info("Skipping execution during build process")
        sys.exit(0)
    
    # Check for required environment variables
    app_url = os.environ.get('APP_URL')
    cron_secret = os.environ.get('CRON_SECRET')
    
    if not app_url or not cron_secret:
        logger.error("Missing required environment variables (APP_URL or CRON_SECRET)")
        sys.exit(1)
    
    # Log execution time
    current_time = datetime.now(timezone.UTC)
    logger.info(f"Evening follow-up reminders cron job started at {current_time.isoformat()}")
    
    # Trigger the follow-up reminders
    success = trigger_followup_reminders()
    
    # Exit with appropriate status code
    sys.exit(0 if success else 1) 