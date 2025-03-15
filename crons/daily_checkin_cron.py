#!/usr/bin/env python3
"""
Daily Check-in Cron Script for the Neurodiversity Accountability System

This script triggers the daily check-in webhook for all users.
It's designed to be executed as a standalone cron job on Railway.

Required environment variables:
- APP_URL: The base URL of the deployed application
- CRON_SECRET: Secret token for webhook authentication
"""

import os
import logging
import requests
import json
from datetime import datetime
from urllib.parse import urljoin
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def trigger_daily_checkin():
    """
    Trigger the daily check-in webhook for all users.
    """
    app_url = os.environ.get('APP_URL')
    cron_secret = os.environ.get('CRON_SECRET')
    
    if not app_url or not cron_secret:
        logger.error("Missing required environment variables (APP_URL or CRON_SECRET)")
        return False
    
    # Construct webhook URL
    webhook_url = urljoin(app_url, '/api/cron/daily-checkin')
    
    # Prepare headers with authentication
    headers = {
        'Content-Type': 'application/json',
        'X-Cron-Secret': cron_secret
    }
    
    # Prepare payload with timestamp
    payload = {
        'timestamp': datetime.utcnow().isoformat()
    }
    
    # Make the request
    try:
        logger.info(f"Triggering daily check-in webhook at {webhook_url}")
        response = requests.post(webhook_url, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            logger.info(f"Daily check-in webhook triggered successfully: {response.text}")
            return True
        else:
            logger.error(f"Failed to trigger daily check-in webhook. Status: {response.status_code}, Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Error triggering daily check-in webhook: {str(e)}")
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
    logger.info(f"Daily check-in cron job started at {datetime.utcnow().isoformat()}")
    
    # Trigger the daily check-in
    success = trigger_daily_checkin()
    
    # Exit with appropriate status code
    sys.exit(0 if success else 1) 