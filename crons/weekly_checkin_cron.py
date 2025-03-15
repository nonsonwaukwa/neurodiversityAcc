#!/usr/bin/env python3
"""
Weekly Check-in Cron Script for the Neurodiversity Accountability System

This script triggers the weekly mental health check-in webhook for all users.
It's designed to be executed as a standalone cron job on Railway once per week.

Required environment variables:
- APP_URL: The base URL of the deployed application
- CRON_SECRET: Secret token for webhook authentication
"""

import os
import logging
import requests
from datetime import datetime
from urllib.parse import urljoin
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def trigger_weekly_checkin():
    """
    Trigger the weekly check-in webhook for all users.
    """
    app_url = os.environ.get('APP_URL')
    cron_secret = os.environ.get('CRON_SECRET')
    
    if not app_url or not cron_secret:
        logger.error("Missing required environment variables (APP_URL or CRON_SECRET)")
        return False
    
    # Construct webhook URL
    webhook_url = urljoin(app_url, '/api/cron/weekly-checkin')
    
    # Get current day of week (0=Monday, 6=Sunday)
    current_day = datetime.utcnow().weekday()
    # Convert to Sunday=0 format as expected by the application
    day_sunday_zero = (current_day + 1) % 7
    
    # Prepare headers with authentication
    headers = {
        'Content-Type': 'application/json',
        'X-Cron-Secret': cron_secret
    }
    
    # Prepare payload with timestamp and day of week
    payload = {
        'timestamp': datetime.utcnow().isoformat(),
        'day_of_week': day_sunday_zero
    }
    
    # Make the request
    try:
        logger.info(f"Triggering weekly check-in webhook at {webhook_url}")
        response = requests.post(webhook_url, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            logger.info(f"Weekly check-in webhook triggered successfully: {response.text}")
            return True
        else:
            logger.error(f"Failed to trigger weekly check-in webhook. Status: {response.status_code}, Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Error triggering weekly check-in webhook: {str(e)}")
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
    logger.info(f"Weekly check-in cron job started at {datetime.utcnow().isoformat()}")
    
    # Trigger the weekly check-in
    success = trigger_weekly_checkin()
    
    # Exit with appropriate status code
    sys.exit(0 if success else 1) 