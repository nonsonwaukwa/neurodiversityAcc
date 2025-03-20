#!/usr/bin/env python3
"""
Morning Follow-up Reminder Cron Script (12:30 PM)

This script triggers the follow-up reminders webhook for users 
who haven't responded to their daily check-ins, 2 hours after the initial check-in.
It's designed to be executed as a standalone cron job on Railway.

Required environment variables:
- APP_URL: The base URL of the deployed application (required on Railway)
- CRON_SECRET: Secret token for webhook authentication
"""

import os
import logging
import requests
import json
from datetime import datetime, timezone, timedelta
from urllib.parse import urljoin
import sys
import firebase_admin
from firebase_admin import credentials, firestore
from app.models.user import User
from app.models.checkin import CheckIn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_eligible_users():
    """
    Check and log which users would be eligible for morning reminders.
    """
    try:
        # Initialize Firebase if not already initialized
        if not firebase_admin._apps:
            cred = credentials.Certificate('./config/firebase-credentials.json')
            firebase_admin.initialize_app(cred)
        
        # Get all active users
        users = User.get_all_active()
        logger.info(f"Found {len(users)} total active users")
        
        eligible_users = []
        current_time = datetime.now(timezone.utc)
        
        for user in users:
            # Get user's last check-in
            last_checkin = CheckIn.get_last_checkin(user.id)
            if last_checkin:
                time_since_checkin = current_time - last_checkin.created_at
                logger.info(f"User {user.name} (ID: {user.id}):")
                logger.info(f"  - Last check-in: {last_checkin.created_at.isoformat()}")
                logger.info(f"  - Time since check-in: {time_since_checkin}")
                
                # Check if user has responded
                has_response = CheckIn.has_response_since(user.id, last_checkin.created_at)
                logger.info(f"  - Has responded: {has_response}")
                
                # Morning reminder window: 1.5-2.5 hours after check-in
                if timedelta(hours=1.5) <= time_since_checkin <= timedelta(hours=2.5) and not has_response:
                    eligible_users.append({
                        'id': user.id,
                        'name': user.name,
                        'last_checkin': last_checkin.created_at.isoformat(),
                        'time_since_checkin': str(time_since_checkin)
                    })
            else:
                logger.info(f"User {user.name} (ID: {user.id}): No check-ins found")
        
        if eligible_users:
            logger.info(f"Found {len(eligible_users)} users eligible for morning reminders:")
            for user in eligible_users:
                logger.info(f"  - {user['name']} (ID: {user['id']})")
                logger.info(f"    Last check-in: {user['last_checkin']}")
                logger.info(f"    Time since check-in: {user['time_since_checkin']}")
        else:
            logger.info("No users are currently eligible for morning reminders")
            
        return len(eligible_users)
        
    except Exception as e:
        logger.error(f"Error checking eligible users: {str(e)}")
        return 0

def trigger_followup_reminders():
    """
    Trigger the follow-up reminders webhook for users who haven't responded to their check-ins.
    """
    # Check eligible users first
    eligible_count = check_eligible_users()
    logger.info(f"Found {eligible_count} users eligible for reminders")
    
    # Prioritize APP_URL as it's the one set in Railway
    app_url = os.environ.get('APP_URL')
    if not app_url:
        logger.error("Missing required environment variable: APP_URL")
        return False
    
    cron_secret = os.environ.get('CRON_SECRET')
    if not cron_secret:
        logger.error("Missing required environment variable: CRON_SECRET")
        return False
    
    # Log environment info
    logger.info(f"Using application URL: {app_url}")
    logger.info(f"CRON_SECRET is {'set' if cron_secret else 'not set'}")
    
    # Construct webhook URL
    webhook_url = urljoin(app_url, '/api/cron/followup-reminders')
    logger.info(f"Constructed webhook URL: {webhook_url}")
    
    # Prepare headers with authentication
    headers = {
        'Content-Type': 'application/json',
        'X-Cron-Secret': cron_secret
    }
    
    # Get current time in UTC
    current_time = datetime.now(timezone.utc)
    
    # Prepare payload with timestamp and reminder type
    payload = {
        'timestamp': current_time.isoformat(),
        'reminder_type': 'morning'  # Indicates this is the morning follow-up
    }
    
    logger.info(f"Sending request at {current_time.isoformat()} UTC")
    logger.info(f"Payload: {json.dumps(payload, indent=2)}")
    
    # Make the request
    try:
        logger.info("Triggering morning follow-up reminders webhook...")
        response = requests.post(webhook_url, headers=headers, json=payload, timeout=30)
        
        logger.info(f"Response status code: {response.status_code}")
        logger.info(f"Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            try:
                response_data = response.json()
                logger.info(f"Success! Response data: {json.dumps(response_data, indent=2)}")
            except json.JSONDecodeError:
                logger.info(f"Success! Response text: {response.text}")
            return True
        else:
            logger.error(f"Failed with status {response.status_code}")
            logger.error(f"Response text: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {str(e)}")
        if hasattr(e, 'response'):
            logger.error(f"Response status code: {e.response.status_code}")
            logger.error(f"Response text: {e.response.text}")
        return False

if __name__ == "__main__":
    # Skip execution during Railway build process
    if os.environ.get('RAILWAY_STATIC_URL'):
        logger.info("Skipping execution during build process")
        sys.exit(0)
    
    # Log execution environment
    logger.info("="*80)
    logger.info("Morning Follow-up Reminder Cron Job Starting")
    logger.info("="*80)
    
    # Log environment variables (safely)
    env_vars = {
        'APP_URL': os.environ.get('APP_URL', 'not set'),
        'CRON_SECRET': 'present' if os.environ.get('CRON_SECRET') else 'not set',
        'RAILWAY_STATIC_URL': os.environ.get('RAILWAY_STATIC_URL', 'not set'),
        'RAILWAY_ENVIRONMENT': os.environ.get('RAILWAY_ENVIRONMENT', 'not set')
    }
    logger.info("Environment Configuration:")
    for key, value in env_vars.items():
        if key != 'CRON_SECRET':
            logger.info(f"  {key}: {value}")
        else:
            logger.info(f"  {key}: {value}")
    
    # Log current time
    current_time = datetime.now(timezone.utc)
    logger.info(f"Current time (UTC): {current_time.isoformat()}")
    
    # Trigger the follow-up reminders
    success = trigger_followup_reminders()
    
    # Log completion
    logger.info("="*80)
    if success:
        logger.info("Morning Follow-up Reminder Cron Job Completed Successfully")
    else:
        logger.error("Morning Follow-up Reminder Cron Job Failed")
    logger.info("="*80)
    
    # Exit with appropriate status code
    sys.exit(0 if success else 1) 