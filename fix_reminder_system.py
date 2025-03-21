#!/usr/bin/env python3
"""
Reminder System Fix Script

This script diagnoses and fixes issues with the reminder system, particularly:
1. Checks WhatsApp API configuration
2. Verifies cron job settings
3. Ensures that reminders will be sent to users who haven't responded
"""

import logging
import sys
import os
from app import create_app
from app.models.user import User
from app.models.checkin import CheckIn
from datetime import datetime, timezone, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_whatsapp_config():
    """Check the WhatsApp API configuration"""
    from flask import current_app
    
    logger.info("Checking WhatsApp API configuration...")
    
    accounts = []
    for i in range(2):  # Check accounts 0 and 1
        phone_id = current_app.config.get(f'WHATSAPP_PHONE_ID_{i}')
        access_token = current_app.config.get(f'WHATSAPP_ACCESS_TOKEN_{i}')
        
        if phone_id and access_token:
            accounts.append({
                'index': i,
                'phone_id': phone_id,
                'access_token': access_token[:10] + '...' if access_token else None
            })
        else:
            logger.warning(f"Account {i} is missing configuration:")
            logger.warning(f"  - WHATSAPP_PHONE_ID_{i}: {'Set' if phone_id else 'Missing'}")
            logger.warning(f"  - WHATSAPP_ACCESS_TOKEN_{i}: {'Set' if access_token else 'Missing'}")
    
    if not accounts:
        logger.error("No WhatsApp accounts configured correctly")
        return False
    
    logger.info(f"Found {len(accounts)} configured WhatsApp accounts")
    return True

def check_cron_settings():
    """Check the cron job settings"""
    from flask import current_app
    
    logger.info("Checking cron job settings...")
    
    cron_enabled = current_app.config.get('ENABLE_CRON')
    cron_secret = current_app.config.get('CRON_SECRET')
    
    if not cron_enabled:
        logger.warning("ENABLE_CRON is not set to True")
    else:
        logger.info("ENABLE_CRON is set to True")
    
    if not cron_secret:
        logger.warning("CRON_SECRET is not set")
    else:
        logger.info("CRON_SECRET is set")
    
    # Check if cron endpoints are accessible
    from werkzeug.test import Client
    from werkzeug.testapp import test_app
    
    client = Client(current_app)
    
    # Try hitting the cron endpoints with the secret
    headers = {'X-Cron-Secret': cron_secret} if cron_secret else {}
    
    # Check if the URL exists by trying to access it with wrong method (HEAD)
    response = client.head('/api/cron/followup-reminders', headers=headers)
    if response.status_code == 405:  # Method Not Allowed means the route exists
        logger.info("Followup reminders endpoint exists")
    else:
        logger.warning(f"Followup reminders endpoint may not exist: status {response.status_code}")
    
    return cron_enabled and cron_secret

def check_reminder_eligibility():
    """Check which users are eligible for reminders"""
    logger.info("Checking reminder eligibility for all users...")
    
    users = User.get_all_active()
    eligible_users = []
    
    for user in users:
        # Get the user's last check-in (sent by system)
        last_checkins = CheckIn.get_for_user(user.user_id, limit=2, is_response=False)
        
        if not last_checkins:
            logger.info(f"User {user.user_id} has no check-ins")
            continue
        
        last_checkin = last_checkins[0]
        
        # Get the user's last response
        last_responses = CheckIn.get_for_user(user.user_id, limit=2, is_response=True)
        
        # If user's last response is newer than our last check-in, they've responded already
        if last_responses and last_responses[0].created_at > last_checkin.created_at:
            logger.info(f"User {user.user_id} already responded to latest check-in")
            continue
        
        # Calculate time since last check-in - ensure timezone-aware comparison
        now = datetime.now(timezone.utc)
        
        # Make sure last_checkin.created_at is timezone-aware
        checkin_time = last_checkin.created_at
        if checkin_time.tzinfo is None:
            # If naive datetime, assume it's in UTC
            checkin_time = checkin_time.replace(tzinfo=timezone.utc)
        
        time_since_checkin = now - checkin_time
        
        # Check if this user is eligible for any reminder
        eligible_for = None
        if timedelta(hours=1.5) < time_since_checkin <= timedelta(hours=2.5):
            eligible_for = "morning"
        elif timedelta(hours=3.5) < time_since_checkin <= timedelta(hours=4.5):
            eligible_for = "midday"
        elif timedelta(hours=7.5) < time_since_checkin <= timedelta(hours=8.5):
            eligible_for = "evening"
        elif time_since_checkin > timedelta(hours=24):
            eligible_for = "nextday"
        
        if eligible_for:
            eligible_users.append({
                'user_id': user.user_id,
                'reminder_type': eligible_for,
                'last_checkin': checkin_time,
                'time_since': time_since_checkin
            })
            logger.info(f"User {user.user_id} eligible for {eligible_for} reminder")
        else:
            logger.info(f"User {user.user_id} not eligible for any reminder at the moment")
    
    logger.info(f"Found {len(eligible_users)} users eligible for reminders")
    return eligible_users

def fix_cron_settings():
    """Fix the cron job settings"""
    from flask import current_app
    
    logger.info("Fixing cron job settings...")
    
    # We can't directly modify config in runtime, so we'll recommend changes
    fixes = []
    
    cron_enabled = current_app.config.get('ENABLE_CRON')
    cron_secret = current_app.config.get('CRON_SECRET')
    
    if not cron_enabled:
        fixes.append("Set ENABLE_CRON=True in your .env file")
    
    if not cron_secret:
        import secrets
        new_secret = secrets.token_hex(16)
        fixes.append(f"Set CRON_SECRET={new_secret} in your .env file")
    
    logger.info("Checking if cron endpoints are registered correctly...")
    
    # Check app structure to ensure we have the cron blueprint registered
    if hasattr(current_app, 'blueprints') and 'cron' in current_app.blueprints:
        logger.info("Cron blueprint is registered in the application")
    else:
        fixes.append("Ensure the cron blueprint is registered in app/__init__.py with: app.register_blueprint(cron_bp, url_prefix='/api')")
    
    if fixes:
        logger.warning("The following fixes should be applied to the cron system:")
        for fix in fixes:
            logger.warning(f" - {fix}")
    else:
        logger.info("Cron settings look good")
    
    return fixes

def print_summary(eligible_users, whatsapp_ok, cron_fixes):
    """Print a summary of the diagnosis"""
    logger.info("\n" + "="*50)
    logger.info("REMINDER SYSTEM DIAGNOSIS SUMMARY")
    logger.info("="*50)
    
    logger.info(f"WhatsApp API Configuration: {'OK' if whatsapp_ok else 'ISSUE DETECTED'}")
    
    if cron_fixes:
        logger.info(f"Cron System: ISSUES DETECTED ({len(cron_fixes)} fixes needed)")
    else:
        logger.info("Cron System: OK")
    
    logger.info(f"Users awaiting follow-up: {len(eligible_users)}")
    
    if eligible_users:
        logger.info("\nUsers eligible for reminders:")
        for user in eligible_users:
            logger.info(f"  - User {user['user_id']}: {user['reminder_type']} reminder (last check-in {user['last_checkin'].isoformat()})")
    
    if not whatsapp_ok or cron_fixes:
        logger.info("\nRECOMMENDED ACTIONS:")
        
        if not whatsapp_ok:
            logger.info("1. Fix WhatsApp API configuration in your .env file by setting:")
            logger.info("   - WHATSAPP_API_URL (usually https://graph.facebook.com/v17.0)")
            logger.info("   - WHATSAPP_PHONE_ID_0")
            logger.info("   - WHATSAPP_ACCESS_TOKEN_0")
        
        if cron_fixes:
            for i, fix in enumerate(cron_fixes):
                logger.info(f"{2 if not whatsapp_ok else 1}.{i+1}. {fix}")
        
        logger.info("\nAfter making these changes, restart the application and run:")
        logger.info("   python fix_reminder_system.py --apply")
    else:
        logger.info("\nREMINDER SYSTEM STATUS: GOOD 👍")
        logger.info("No issues detected. The reminder system should be working correctly.")
        
        if eligible_users:
            logger.info("\nTo manually send reminders to eligible users, run:")
            logger.info("   python fix_reminder_system.py --apply")

def manually_send_reminders(eligible_users):
    """Manually send reminders to eligible users"""
    logger.info("Manually sending reminders to eligible users...")
    
    if not eligible_users:
        logger.info("No users eligible for reminders at the moment")
        return
    
    # Import here to avoid circular imports
    from app.cron.reminders import send_checkin_reminders
    
    # Try the automatic way first
    logger.info("Attempting to send reminders using the built-in function...")
    try:
        send_checkin_reminders()
        logger.info("Successfully triggered reminder system")
    except Exception as e:
        logger.error(f"Error using built-in reminder function: {str(e)}")
        logger.info("Falling back to manual per-user reminders...")
        
        # Import and use our manual reminder function
        from app.services.whatsapp import get_whatsapp_service
        
        for user_data in eligible_users:
            user_id = user_data['user_id']
            reminder_type = user_data['reminder_type']
            
            try:
                user = User.get(user_id)
                if not user:
                    logger.error(f"User with ID {user_id} not found")
                    continue
                
                whatsapp_service = get_whatsapp_service(user.account_index)
                
                logger.info(f"Sending {reminder_type} reminder to user {user_id}")
                
                if reminder_type == 'morning':
                    message = (
                        f"Hey {user.name}! 💫 Just a gentle check-in - absolutely no pressure at all. "
                        f"I'm still here whenever you feel ready to connect. "
                        f"If you'd like, you could:"
                    )
                    buttons = [
                        {"id": "plan_day", "title": "Plan my day"},
                        {"id": "quick_checkin", "title": "Quick hello"},
                        {"id": "remind_later", "title": "Not just now"}
                    ]
                    whatsapp_service.send_interactive_buttons(user_id, message, buttons)
                
                elif reminder_type == 'midday':
                    message = (
                        f"Hi {user.name}! 🌤️ The day still holds possibilities, and that's wonderful. "
                        f"If it feels right for you, maybe you'd like to:"
                    )
                    buttons = [
                        {"id": "plan_afternoon", "title": "Plan afternoon"},
                        {"id": "self_care", "title": "Self-care time"},
                        {"id": "just_chat", "title": "Just chat"}
                    ]
                    whatsapp_service.send_interactive_buttons(user_id, message, buttons)
                
                elif reminder_type == 'evening':
                    from app.services.tasks import get_task_service
                    task_service = get_task_service()
                    self_care_tip = task_service.get_self_care_tip()
                    
                    message = (
                        f"Hey {user.name}! ✨ How has your day unfolded? Remember, each day is its own journey, "
                        f"and tomorrow offers a fresh beginning whenever you need it.\n\n"
                        f"Here's a gentle self-care reminder if it feels helpful: {self_care_tip}\n\n"
                        f"If you'd like, you could:"
                    )
                    buttons = [
                        {"id": "share_day", "title": "Share about today"},
                        {"id": "plan_tomorrow", "title": "Gentle tomorrow plan"},
                        {"id": "rest_now", "title": "Rest & recharge"}
                    ]
                    whatsapp_service.send_interactive_buttons(user_id, message, buttons)
                
                elif reminder_type == 'nextday':
                    message = (
                        f"Hi {user.name} 💖, I've noticed we haven't connected in a little while, and that's completely okay! "
                        f"Sometimes we need space or things get busy, and I'm here with warmth whenever you're ready. "
                        f"No rush at all. If you'd like to reconnect, maybe you'd enjoy:"
                    )
                    buttons = [
                        {"id": "fresh_start", "title": "Fresh beginning"},
                        {"id": "gentle_checkin", "title": "Just say hi"},
                        {"id": "need_help", "title": "Gentle support"}
                    ]
                    whatsapp_service.send_interactive_buttons(user_id, message, buttons)
                
                logger.info(f"Successfully sent {reminder_type} reminder to user {user_id}")
                
            except Exception as e:
                logger.error(f"Error sending reminder to user {user_id}: {str(e)}")

if __name__ == "__main__":
    # Check if we should apply fixes
    apply_fixes = "--apply" in sys.argv
    
    # Create Flask app and set up application context
    app = create_app()
    with app.app_context():
        # Run diagnostic checks
        whatsapp_ok = check_whatsapp_config()
        cron_fixes = fix_cron_settings() if apply_fixes else check_cron_settings()
        eligible_users = check_reminder_eligibility()
        
        # Print summary
        print_summary(eligible_users, whatsapp_ok, cron_fixes)
        
        # Apply fixes if requested
        if apply_fixes and eligible_users:
            logger.info("\nApplying fixes and sending reminders...")
            manually_send_reminders(eligible_users)
        elif apply_fixes:
            logger.info("\nNo users eligible for reminders at the moment.")
            logger.info("The system will send reminders automatically when users become eligible.") 