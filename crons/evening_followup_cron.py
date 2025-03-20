#!/usr/bin/env python3
"""
Evening Follow-up Reminder Cron Script (6:30 PM)

This script triggers the follow-up reminders webhook for users 
who haven't responded to their daily check-ins, 8 hours after the initial check-in.
It's designed to be executed as a standalone cron job on Railway.

Required environment variables:
- APP_URL: The base URL of the deployed application (required on Railway)
- CRON_SECRET: Secret token for webhook authentication
- FIREBASE_CREDENTIALS: Firebase service account credentials JSON
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_eligible_users():
    """Check for users eligible for follow-up reminders."""
    try:
        # Get Firebase credentials from environment
        creds_json = os.environ.get('FIREBASE_CREDENTIALS')
        if not creds_json:
            logger.error("FIREBASE_CREDENTIALS environment variable not set")
            return []
            
        try:
            creds_dict = json.loads(creds_json)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse FIREBASE_CREDENTIALS JSON: {e}")
            return []
            
        # Initialize Firebase Admin
        try:
            cred = credentials.Certificate(creds_dict)
            firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Firebase Admin: {e}")
            return []

        # Get Firestore client
        db = firestore.client()
        
        # Get current time in UTC
        current_time = datetime.now(timezone.utc)
        logger.info(f"Checking for eligible users at {current_time.isoformat()}")
        
        # Query for active users
        users_ref = db.collection('users')
        active_users = users_ref.where('last_active', '!=', None).stream()
        
        # Convert to list and log count
        active_users_list = list(active_users)
        logger.info(f"Found {len(active_users_list)} active users")
        
        eligible_users = []
        for user in active_users_list:
            user_data = user.to_dict()
            user_id = user.id
            
            # Get user's latest check-in
            checkins_ref = db.collection('checkins')
            latest_checkin = checkins_ref.where(
                'user_id', '==', user_id
            ).where(
                'is_response', '==', False
            ).order_by(
                'created_at', direction=firestore.Query.DESCENDING
            ).limit(1).stream()
            
            latest_checkin_list = list(latest_checkin)
            if not latest_checkin_list:
                logger.info(f"No check-ins found for user {user_id}")
                continue
                
            latest_checkin_data = latest_checkin_list[0].to_dict()
            checkin_time = latest_checkin_data.get('created_at')
            
            if not checkin_time:
                logger.warning(f"Check-in for user {user_id} has no timestamp")
                continue
                
            # Convert to datetime if string
            if isinstance(checkin_time, str):
                try:
                    checkin_time = datetime.fromisoformat(checkin_time.replace('Z', '+00:00'))
                except ValueError as e:
                    logger.error(f"Failed to parse check-in timestamp for user {user_id}: {e}")
                    continue
            
            # Calculate time since check-in
            time_since_checkin = current_time - checkin_time
            logger.info(f"User {user_id} last check-in was {time_since_checkin} ago")
            
            # Check if user has responded
            responses = checkins_ref.where(
                'user_id', '==', user_id
            ).where(
                'is_response', '==', True
            ).where(
                'created_at', '>', checkin_time
            ).limit(1).stream()
            
            has_responded = len(list(responses)) > 0
            if has_responded:
                logger.info(f"User {user_id} has already responded to their latest check-in")
                continue
                
            # Check if within reminder window (8 hours after check-in)
            if timedelta(hours=7.5) <= time_since_checkin <= timedelta(hours=8.5):
                logger.info(f"User {user_id} is eligible for an evening follow-up reminder")
                eligible_users.append({
                    'id': user_id,
                    'phone': user_id,  # WhatsApp number is stored in user_id
                    'name': user_data.get('name', f"User_{user_id[-4:]}"),
                    'checkinTime': checkin_time,
                    'timeSinceCheckin': time_since_checkin
                })
            else:
                logger.info(f"User {user_id} is not in the evening follow-up window")
        
        logger.info(f"Found {len(eligible_users)} users eligible for evening follow-up reminders")
        return eligible_users
        
    except Exception as e:
        logger.error(f"Error checking eligible users: {e}")
        return []
        
    finally:
        # Clean up Firebase Admin
        try:
            firebase_admin.delete_app(firebase_admin.get_app())
            logger.info("Firebase Admin cleaned up successfully")
        except Exception as e:
            logger.warning(f"Failed to clean up Firebase Admin: {e}")

def trigger_followup_reminders():
    """Trigger follow-up reminders for eligible users."""
    try:
        # Check environment variables
        app_url = os.environ.get('APP_URL')
        cron_secret = os.environ.get('CRON_SECRET')
        
        if not app_url or not cron_secret:
            logger.error("Missing required environment variables (APP_URL or CRON_SECRET)")
            return False
            
        # Get eligible users
        eligible_users = check_eligible_users()
        if not eligible_users:
            logger.info("No users eligible for follow-up reminders")
            return True
            
        # Group users by phone number (account)
        users_by_account = {}
        for user in eligible_users:
            phone = user.get('phone')
            if not phone:
                logger.warning(f"User {user['id']} has no phone number")
                continue
            if phone not in users_by_account:
                users_by_account[phone] = []
            users_by_account[phone].append(user)
            
        logger.info(f"Found {len(users_by_account)} accounts with eligible users")
        
        # Call webhook for each account
        webhook_url = f"{app_url.rstrip('/')}/api/cron/followup-reminders"
        headers = {
            'Content-Type': 'application/json',
            'X-Cron-Secret': cron_secret
        }
        
        success_count = 0
        for account_phone, account_users in users_by_account.items():
            try:
                data = {
                    'type': 'evening',
                    'users': [user['id'] for user in account_users]
                }
                
                response = requests.post(webhook_url, json=data, headers=headers)
                
                if response.status_code == 200:
                    logger.info(f"Successfully triggered reminders for account {account_phone}")
                    success_count += 1
                else:
                    logger.error(f"Failed to trigger reminders for account {account_phone}: {response.status_code} - {response.text}")
                    
            except Exception as e:
                logger.error(f"Error triggering reminders for account {account_phone}: {e}")
                
        logger.info(f"Successfully triggered reminders for {success_count}/{len(users_by_account)} accounts")
        return success_count > 0 or len(users_by_account) == 0
        
    except Exception as e:
        logger.error(f"Error triggering follow-up reminders: {e}")
        return False

if __name__ == "__main__":
    # Skip execution during Railway build process
    if os.environ.get('RAILWAY_STATIC_URL'):
        logger.info("Skipping execution during build process")
        sys.exit(0)
    
    # Log execution environment
    logger.info("="*80)
    logger.info("Evening Follow-up Reminder Cron Job Starting")
    logger.info("="*80)
    
    # Log environment variables (safely)
    env_vars = {
        'APP_URL': os.environ.get('APP_URL', 'not set'),
        'CRON_SECRET': 'present' if os.environ.get('CRON_SECRET') else 'not set',
        'FIREBASE_CREDENTIALS': 'present' if os.environ.get('FIREBASE_CREDENTIALS') else 'not set',
        'RAILWAY_STATIC_URL': os.environ.get('RAILWAY_STATIC_URL', 'not set'),
        'RAILWAY_ENVIRONMENT': os.environ.get('RAILWAY_ENVIRONMENT', 'not set')
    }
    logger.info("Environment Configuration:")
    for key, value in env_vars.items():
        if key not in ['CRON_SECRET', 'FIREBASE_CREDENTIALS']:
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
        logger.info("Evening Follow-up Reminder Cron Job Completed Successfully")
    else:
        logger.error("Evening Follow-up Reminder Cron Job Failed")
    logger.info("="*80)
    
    # Exit with appropriate status code
    sys.exit(0 if success else 1) 