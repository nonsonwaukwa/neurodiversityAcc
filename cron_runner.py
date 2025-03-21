#!/usr/bin/env python3
"""
Cron Job Runner

This script allows manual execution of cron jobs for testing and verification.
Particularly useful for testing the follow-up reminder system.
"""

import logging
import sys
from app import create_app
import requests
import os
import json
from datetime import datetime, timezone

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_cron_job(cron_type, params=None):
    """
    Manually run a cron job by sending a request to the cron endpoint
    
    Args:
        cron_type (str): Type of cron job to run (e.g., 'followup-reminders')
        params (dict, optional): Additional parameters to send with the request
    """
    app = create_app()
    
    # Get the cron secret from Flask config
    with app.app_context():
        cron_secret = app.config.get('CRON_SECRET')
        if not cron_secret:
            logger.error("CRON_SECRET is not set in configuration")
            return False
    
    # Set up headers and payload
    headers = {'X-Cron-Secret': cron_secret, 'Content-Type': 'application/json'}
    payload = params or {}
    
    # Try both URL patterns - with and without /api prefix
    # Some Flask setups use /api as a prefix, others don't
    urls = [
        f'http://localhost:5000/api/cron/{cron_type}',
        f'http://localhost:5000/cron/{cron_type}'
    ]
    
    for url in urls:
        logger.info(f"Trying request to {url} with payload: {json.dumps(payload)}")
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            logger.info(f"Response status: {response.status_code}")
            logger.info(f"Response body: {response.text}")
            
            if response.status_code == 200:
                logger.info(f"Successfully ran {cron_type} cron job")
                return True
            elif response.status_code != 404:  # If we get anything other than 404, we found the endpoint but had another issue
                logger.error(f"Failed to run {cron_type} cron job: {response.text}")
                return False
            # If we get 404, try the next URL pattern
            
        except requests.exceptions.ConnectionError:
            logger.warning(f"Could not connect to {url}. Is the Flask app running?")
        except Exception as e:
            logger.error(f"Error running cron job: {str(e)}")
            return False
    
    # If we reach here, we tried all URL patterns and none worked
    logger.error("Failed to reach cron endpoint. Make sure the Flask app is running on port 5000.")
    return False

def run_reminder_cron(reminder_type=None):
    """
    Run the follow-up reminders cron job
    
    Args:
        reminder_type (str, optional): Type of reminder to send ('morning', 'midday', 'evening', 'nextday')
    """
    params = {}
    if reminder_type:
        params['reminder_type'] = reminder_type
    
    return run_cron_job('followup-reminders', params)

def simulate_railway_cron():
    """Simulate how Railway would trigger the cron jobs"""
    # Get the Flask app
    app = create_app()
    
    # Get the cron secret from Flask config
    with app.app_context():
        cron_secret = app.config.get('CRON_SECRET')
        if not cron_secret:
            logger.error("CRON_SECRET is not set in configuration")
            return False
    
    # Get current hour in UTC
    current_hour = datetime.now(timezone.utc).hour
    
    # Determine which reminder to run based on time of day
    if 10 <= current_hour < 13:  # Late morning
        reminder_type = 'morning'
    elif 13 <= current_hour < 16:  # Afternoon
        reminder_type = 'midday'
    elif 16 <= current_hour < 20:  # Evening
        reminder_type = 'evening'
    else:  # Night/early morning - check for any long-overdue reminders
        reminder_type = 'nextday'
    
    logger.info(f"Based on current hour ({current_hour} UTC), running '{reminder_type}' reminders")
    return run_reminder_cron(reminder_type)

if __name__ == "__main__":
    # Default to simulating Railway's cron behavior
    if len(sys.argv) == 1 or sys.argv[1] == '--auto':
        simulate_railway_cron()
    elif sys.argv[1] == '--help':
        print("Usage: python cron_runner.py [OPTION]")
        print("Run cron jobs for testing purposes")
        print("\nOptions:")
        print("  --auto               Automatically choose the right reminder type based on time of day")
        print("  --morning            Run morning reminders (1.5-2.5 hours after check-in)")
        print("  --midday             Run midday reminders (3.5-4.5 hours after check-in)")
        print("  --evening            Run evening reminders (7.5-8.5 hours after check-in)")
        print("  --nextday            Run next-day reminders (>24 hours after check-in)")
        print("  --all                Run all reminder types")
        print("  --help               Display this help message")
    elif sys.argv[1] == '--morning':
        run_reminder_cron('morning')
    elif sys.argv[1] == '--midday':
        run_reminder_cron('midday')
    elif sys.argv[1] == '--evening':
        run_reminder_cron('evening')
    elif sys.argv[1] == '--nextday':
        run_reminder_cron('nextday')
    elif sys.argv[1] == '--all':
        run_reminder_cron()
    else:
        print(f"Unknown option: {sys.argv[1]}")
        print("Use --help to see available options") 