#!/usr/bin/env python3
"""
Reminder Debugging Tool

This script diagnoses why follow-up reminders aren't being sent even though
the cron job is running successfully.
"""

import logging
import sys
from app import create_app
from app.models.user import User
from app.models.checkin import CheckIn
from datetime import datetime, timezone, timedelta
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# User ID to check
TARGET_USER_ID = "2348023672476"

def check_reminder_settings():
    """Check if reminder system settings are configured correctly"""
    from flask import current_app
    
    logger.info("=" * 80)
    logger.info("REMINDER SYSTEM CONFIGURATION CHECK")
    logger.info("=" * 80)
    
    # Check WhatsApp configuration
    whatsapp_api_url = current_app.config.get('WHATSAPP_API_URL')
    logger.info(f"WhatsApp API URL: {whatsapp_api_url or 'NOT SET'}")
    
    found_account = False
    for i in range(5):  # Check up to 5 accounts
        phone_id = current_app.config.get(f'WHATSAPP_PHONE_ID_{i}')
        access_token = current_app.config.get(f'WHATSAPP_ACCESS_TOKEN_{i}')
        
        if phone_id and access_token:
            found_account = True
            token_preview = access_token[:10] + "..." if len(access_token) > 10 else "TOO SHORT!"
            logger.info(f"WhatsApp Account {i} configured:")
            logger.info(f"  - Phone ID: {phone_id}")
            logger.info(f"  - Access Token: {token_preview}")
    
    if not found_account:
        logger.error("❌ NO WHATSAPP ACCOUNTS CONFIGURED!")
    
    # Check cron settings
    cron_enabled = current_app.config.get('ENABLE_CRON')
    cron_secret = current_app.config.get('CRON_SECRET')
    
    logger.info(f"Cron Enabled: {cron_enabled}")
    logger.info(f"Cron Secret: {'Set' if cron_secret else 'NOT SET'}")
    
    return found_account and cron_enabled and cron_secret

def get_user_data(user_id):
    """Get user data and check-ins"""
    user = User.get(user_id)
    
    if not user:
        logger.error(f"❌ User {user_id} not found!")
        return None, None, None
    
    logger.info("=" * 80)
    logger.info(f"USER DATA: {user_id}")
    logger.info("=" * 80)
    logger.info(f"Name: {user.name}")
    logger.info(f"Account Index: {user.account_index}")
    logger.info(f"Last Active: {user.last_active}")
    
    # Get check-ins
    all_checkins = CheckIn.get_for_user(user_id, limit=20)
    
    # Separate system messages and user responses
    system_messages = []
    user_responses = []
    
    for checkin in all_checkins:
        data = checkin.to_dict()
        created_at = data.get('created_at')
        
        # Skip check-ins without timestamps
        if not created_at:
            continue
        
        # Make sure timestamp is timezone-aware
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        
        if hasattr(checkin, 'is_response') and checkin.is_response:
            user_responses.append({
                'id': data.get('checkin_id'),
                'content': data.get('response'),
                'time': created_at
            })
        else:
            system_messages.append({
                'id': data.get('checkin_id'),
                'content': data.get('response'),
                'time': created_at
            })
    
    # Sort by time (newest first)
    user_responses.sort(key=lambda x: x['time'], reverse=True)
    system_messages.sort(key=lambda x: x['time'], reverse=True)
    
    logger.info(f"Found {len(user_responses)} user responses and {len(system_messages)} system messages")
    
    return user, user_responses, system_messages

def check_reminder_eligibility(user, user_responses, system_messages):
    """Check if user is eligible for reminders and which type"""
    
    logger.info("=" * 80)
    logger.info("REMINDER ELIGIBILITY CHECK")
    logger.info("=" * 80)
    
    if not system_messages:
        logger.info("No system messages found to check for reminder eligibility")
        return None
    
    # Get the latest system message
    latest_system = system_messages[0]
    logger.info(f"Latest system message: {latest_system['time'].isoformat()}")
    logger.info(f"Content: {latest_system['content'][:50]}...")
    
    # Check if user has already responded to the latest system message
    latest_response = user_responses[0] if user_responses else None
    
    if latest_response:
        logger.info(f"Latest user response: {latest_response['time'].isoformat()}")
        logger.info(f"Content: {latest_response['content'][:50]}...")
        
        if latest_response['time'] > latest_system['time']:
            logger.info("✅ User has already responded to the latest system message - no reminder needed")
            return None
    else:
        logger.info("No user responses found")
    
    # Calculate time since the latest system message
    now = datetime.now(timezone.utc)
    logger.info(f"Current time (UTC): {now.isoformat()}")
    
    time_since_checkin = now - latest_system['time']
    logger.info(f"Time since last check-in: {time_since_checkin}")
    
    # Check all reminder windows
    windows = [
        ("morning", timedelta(hours=1.5), timedelta(hours=2.5)),
        ("midday", timedelta(hours=3.5), timedelta(hours=4.5)),
        ("evening", timedelta(hours=7.5), timedelta(hours=8.5)),
        ("nextday", timedelta(hours=24), timedelta(days=365))  # Very large upper bound
    ]
    
    eligible_type = None
    for reminder_type, min_time, max_time in windows:
        is_eligible = (
            min_time < time_since_checkin <= max_time 
            if reminder_type != "nextday" 
            else time_since_checkin > min_time
        )
        
        status = "ELIGIBLE ✅" if is_eligible else "not eligible ❌"
        logger.info(f"{reminder_type} reminder: {status}")
        
        if is_eligible and not eligible_type:
            eligible_type = reminder_type
    
    return eligible_type

def test_whatsapp_service(user):
    """Try to send a test message via WhatsApp to diagnose issues"""
    from app.services.whatsapp import get_whatsapp_service
    
    logger.info("=" * 80)
    logger.info("WHATSAPP SERVICE TEST")
    logger.info("=" * 80)
    
    try:
        # Get the WhatsApp service for the user's account
        whatsapp_service = get_whatsapp_service(user.account_index)
        
        # Try a direct message call
        logger.info(f"Attempting to send a test message to user {user.user_id}")
        
        test_message = (
            "🔍 This is a diagnostic test message from the reminder debugging tool. "
            "If you received this, your WhatsApp configuration is working correctly."
        )
        
        # Don't actually send the message to avoid spamming the user
        # Instead, test connection only
        has_connection = whatsapp_service.check_connection()
        
        if has_connection:
            logger.info("✅ WhatsApp service connection test SUCCESSFUL")
            logger.info("Your WhatsApp configuration appears to be working, but actual message sending is disabled in this diagnostic tool")
        else:
            logger.error("❌ WhatsApp service connection test FAILED")
            logger.error("Unable to connect to WhatsApp API")
            
        # Check additional WhatsApp configuration info
        account_info = whatsapp_service.get_account_info()
        if account_info:
            logger.info(f"WhatsApp Account Info: {account_info}")
        
        return has_connection
        
    except Exception as e:
        logger.error(f"❌ Error testing WhatsApp service: {str(e)}")
        return False

def print_recommendations(user, eligible_type, whatsapp_working):
    """Print recommendations based on diagnostic results"""
    
    logger.info("=" * 80)
    logger.info("DIAGNOSIS RESULTS AND RECOMMENDATIONS")
    logger.info("=" * 80)
    
    if not user:
        logger.error("❌ USER NOT FOUND - Please check the user ID in the script")
        return
    
    if not eligible_type:
        logger.info("🔍 You are currently NOT ELIGIBLE for any reminder type")
        logger.info("Possible reasons:")
        logger.info("  1. You already responded to the latest check-in")
        logger.info("  2. Not enough time has passed since the latest check-in")
        logger.info("  3. Too much time has passed for the reminders you're testing")
        
        logger.info("\nRecommendations:")
        logger.info("  - Wait until you fall into one of the reminder windows")
        logger.info("  - Try testing with a different reminder type (especially 'nextday')")
        logger.info("  - Create a new check-in to reset the timers")
    else:
        logger.info(f"✅ You ARE ELIGIBLE for a {eligible_type} reminder")
        
        if not whatsapp_working:
            logger.error("❌ WhatsApp integration is NOT WORKING")
            logger.info("\nRecommendations:")
            logger.info("  1. Check your WhatsApp API credentials in the .env file")
            logger.info("  2. Make sure your WhatsApp Business account is active")
            logger.info("  3. Verify the Phone ID is correct")
        else:
            logger.info("✅ WhatsApp integration appears to be working")
            logger.info("\nRecommendations:")
            logger.info("  1. Verify that the remind_type in the cron job matches your eligible type")
            logger.info("  2. Check Railway logs for any errors during message sending")
            logger.info("  3. Try sending a direct test message using send_direct_reminder.py")

if __name__ == "__main__":
    # Get command line arguments
    user_id = TARGET_USER_ID
    if len(sys.argv) > 1:
        user_id = sys.argv[1]
    
    # Create Flask app and set up application context
    app = create_app()
    with app.app_context():
        # Run diagnostics
        settings_ok = check_reminder_settings()
        
        user, user_responses, system_messages = get_user_data(user_id)
        if not user:
            sys.exit(1)
            
        eligible_type = check_reminder_eligibility(user, user_responses, system_messages)
        
        whatsapp_working = test_whatsapp_service(user)
        
        print_recommendations(user, eligible_type, whatsapp_working) 