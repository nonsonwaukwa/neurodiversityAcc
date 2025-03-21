#!/usr/bin/env python3
"""
Railway Cron Trigger

This script triggers the follow-up reminders cron job directly on the Railway deployment.
It requires the CRON_SECRET to be set as an environment variable or provided as a command-line argument.
"""

import logging
import sys
import requests
import os
import json
import argparse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def trigger_railway_cron(reminder_type="morning", cron_secret=None, base_url=None):
    """
    Trigger the follow-up reminders cron job on Railway
    
    Args:
        reminder_type (str): Type of reminder to send ("morning", "midday", "evening", "nextday")
        cron_secret (str): The secret key for authenticating with the cron endpoint
        base_url (str): The base URL of the Railway deployment
        
    Returns:
        bool: True if the request was successful, False otherwise
    """
    # Get the cron secret from environment variables if not provided
    if not cron_secret:
        cron_secret = os.environ.get("CRON_SECRET")
        
    if not cron_secret:
        logger.error("CRON_SECRET not found in environment and not provided as an argument")
        return False
    
    # Set default base URL if not provided
    if not base_url:
        base_url = os.environ.get("BASE_URL", "https://neurodiversityacc.up.railway.app")
    
    # Build request
    url = f"{base_url}/api/cron/followup-reminders"
    headers = {
        "X-Cron-Secret": cron_secret,
        "Content-Type": "application/json"
    }
    payload = {"reminder_type": reminder_type}
    
    logger.info(f"Triggering {reminder_type} follow-up reminders on Railway")
    logger.info(f"URL: {url}")
    
    try:
        # Make request
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        
        logger.info(f"Status code: {response.status_code}")
        if response.status_code == 200:
            logger.info(f"Response: {json.dumps(response.json(), indent=2)}")
            logger.info(f"Successfully triggered {reminder_type} reminders!")
            return True
        else:
            logger.error(f"Failed to trigger reminders: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Error triggering reminders: {str(e)}")
        return False

if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Trigger follow-up reminders cron job on Railway")
    parser.add_argument("reminder_type", nargs="?", default="morning", 
                        choices=["morning", "midday", "evening", "nextday"],
                        help="Type of reminder to send")
    parser.add_argument("--secret", "-s", help="Cron secret key for authentication")
    parser.add_argument("--url", "-u", help="Base URL of the Railway deployment")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Trigger the cron job
    success = trigger_railway_cron(
        reminder_type=args.reminder_type,
        cron_secret=args.secret,
        base_url=args.url
    )
    
    # Exit with appropriate status code
    sys.exit(0 if success else 1) 