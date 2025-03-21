#!/usr/bin/env python3
"""
Time Simulator for Midday Reminder

This script simulates the current time to be within the midday reminder window
to test if a user would be eligible for a midday reminder.
"""

import logging
from datetime import datetime, timezone, timedelta
import sys
from app.models.user import User
from app.models.checkin import CheckIn
from app import create_app

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# User ID to check
TARGET_USER_ID = "2348023672476"

def simulate_reminder_eligibility(hours_offset=None):
    """
    Simulate being in different time periods to check reminder eligibility
    
    Args:
        hours_offset (float): Hours to add to the latest check-in time (if None, will test all windows)
    """
    logger.info("="*80)
    logger.info("SIMULATING REMINDER ELIGIBILITY")
    logger.info("="*80)
    
    # Get the latest system message
    last_checkins = CheckIn.get_for_user(TARGET_USER_ID, limit=1, is_response=False)
    
    if not last_checkins:
        logger.error(f"No check-ins found for user {TARGET_USER_ID}")
        return
        
    last_checkin = last_checkins[0]
    checkin_time = last_checkin.created_at
    
    # Get the user's last response
    last_responses = CheckIn.get_for_user(TARGET_USER_ID, limit=1, is_response=True)
    has_responded = False
    
    if last_responses:
        response_time = last_responses[0].created_at
        if response_time > checkin_time:
            has_responded = True
            logger.info(f"User has already responded to the latest check-in")
            logger.info(f"Latest system message: {checkin_time}")
            logger.info(f"Latest user response: {response_time}")
    
    if has_responded:
        logger.info("User is not eligible for any reminders because they've already responded")
        return
    
    # Define our reminder windows
    windows = [
        ("morning", 1.5, 2.5),
        ("midday", 3.5, 4.5),
        ("evening", 7.5, 8.5),
        ("nextday", 24, 365 * 24)  # Very large upper bound
    ]
    
    # If specific hours offset is provided, only test that window
    if hours_offset is not None:
        # Simulate time at specific offset from check-in
        simulated_time = checkin_time + timedelta(hours=hours_offset)
        logger.info(f"Simulating time at {hours_offset} hours after check-in: {simulated_time}")
        
        # Calculate time since check-in
        time_since_checkin = timedelta(hours=hours_offset)
        
        # Check which window we're in
        for reminder_type, min_hours, max_hours in windows:
            if min_hours < hours_offset <= max_hours:
                logger.info(f"ELIGIBLE FOR {reminder_type.upper()} REMINDER")
                logger.info(f"Time since check-in: {time_since_checkin}")
                logger.info(f"{reminder_type} window: {min_hours}-{max_hours} hours after check-in")
                return reminder_type
        
        logger.info("NOT in any reminder window")
        return None
    
    # Test all reminder windows
    for reminder_type, min_hours, max_hours in windows:
        # Calculate times for this window
        min_time = checkin_time + timedelta(hours=min_hours)
        max_time = checkin_time + timedelta(hours=max_hours)
        
        # Calculate middle of window
        mid_window = checkin_time + timedelta(hours=(min_hours + max_hours) / 2)
        hours_offset = (min_hours + max_hours) / 2
        
        logger.info("-"*60)
        logger.info(f"Testing {reminder_type} reminder window")
        logger.info(f"Window times: {min_time} to {max_time}")
        logger.info(f"Simulating time at {hours_offset} hours after check-in: {mid_window}")
        
        logger.info(f"ELIGIBLE FOR {reminder_type.upper()} REMINDER at this time")
    
    now = datetime.now(timezone.utc)
    actual_time_since_checkin = now - checkin_time
    actual_hours = actual_time_since_checkin.total_seconds() / 3600
    
    logger.info("-"*60)
    logger.info("CURRENT ACTUAL STATUS:")
    logger.info(f"Current time: {now}")
    logger.info(f"Latest check-in: {checkin_time}")
    logger.info(f"Actual time since check-in: {actual_time_since_checkin} ({actual_hours:.2f} hours)")
    
    for reminder_type, min_hours, max_hours in windows:
        if min_hours < actual_hours <= max_hours:
            logger.info(f"CURRENTLY ELIGIBLE FOR {reminder_type.upper()} REMINDER")
            break
    else:
        logger.info("Currently NOT eligible for any reminder")
    
    # Calculate time until eligible for midday reminder
    if actual_hours <= 3.5:
        time_until_midday = (checkin_time + timedelta(hours=3.5)) - now
        logger.info(f"Time until midday reminder eligibility: {time_until_midday}")

if __name__ == "__main__":
    # Parse command line args
    hours_offset = None
    if len(sys.argv) > 1:
        try:
            hours_offset = float(sys.argv[1])
        except ValueError:
            logger.error(f"Invalid hours offset: {sys.argv[1]}. Must be a number.")
            sys.exit(1)
    
    # Create Flask app and context
    app = create_app()
    with app.app_context():
        simulate_reminder_eligibility(hours_offset) 