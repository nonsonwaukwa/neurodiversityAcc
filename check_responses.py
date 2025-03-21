from config.firebase_config import get_db
import logging
from datetime import datetime, timedelta, timezone

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.info("Checking for user responses")

# Connect to the database
db = get_db()

# Get all check-ins for the user and filter in Python
query = db.collection('checkins').where('user_id', '==', '2348023672476').order_by('created_at', direction='DESCENDING').limit(20)
print("Query created, fetching results...")

try:
    results = list(query.stream())
    print(f'Found {len(results)} check-ins')
    
    system_messages = []
    user_responses = []
    
    for doc in results:
        data = doc.to_dict()
        is_response = data.get('is_response', False)
        
        created_at = data.get('created_at')
        if created_at:
            timestamp_str = str(created_at)
        else:
            timestamp_str = "None"
        
        if is_response:
            user_responses.append({
                'id': doc.id,
                'response': data.get('response'),
                'time': created_at,
                'time_str': timestamp_str
            })
        else:
            system_messages.append({
                'id': doc.id,
                'message': data.get('response'),
                'time': created_at,
                'time_str': timestamp_str
            })
    
    print(f"\nUser Responses: {len(user_responses)}")
    print('-' * 50)
    for resp in user_responses:
        print(f'Response: {resp["response"]}')
        print(f'Time: {resp["time_str"]}')
        print('-' * 50)
    
    print(f"\nSystem Messages: {len(system_messages)}")
    print('-' * 50)
    for msg in system_messages:
        print(f'Message: {msg["message"]}')
        print(f'Time: {msg["time_str"]}')
        print('-' * 50)
    
    # Check for the followup conditions based on the reminders.py logic
    print("\nReminder Eligibility Analysis:")
    print('-' * 50)
    
    if not user_responses:
        print("No user responses found. User has never responded to check-ins.")
        
        if system_messages:
            latest_system_message = system_messages[0]
            system_time = latest_system_message['time']
            
            # Make sure we have timezone-aware datetime for comparison
            now = datetime.now(timezone.utc)
            
            # Calculate time difference
            time_since_checkin = now - system_time
            
            print(f"Latest system message: {system_time}")
            print(f"Current time (UTC): {now}")
            print(f"Time since check-in: {time_since_checkin}")
            
            # Check reminder windows
            if timedelta(hours=1.5) < time_since_checkin <= timedelta(hours=2.5):
                print("ELIGIBLE for first follow-up (morning reminder)")
                print(f"Morning window: {system_time + timedelta(hours=1.5)} to {system_time + timedelta(hours=2.5)}")
            elif timedelta(hours=3.5) < time_since_checkin <= timedelta(hours=4.5):
                print("ELIGIBLE for mid-day check")
                print(f"Mid-day window: {system_time + timedelta(hours=3.5)} to {system_time + timedelta(hours=4.5)}")
            elif timedelta(hours=7.5) < time_since_checkin <= timedelta(hours=8.5):
                print("ELIGIBLE for evening reset")
                print(f"Evening window: {system_time + timedelta(hours=7.5)} to {system_time + timedelta(hours=8.5)}")
            elif time_since_checkin > timedelta(hours=24):
                print("ELIGIBLE for next day support")
                print(f"Next day support: After {system_time + timedelta(hours=24)}")
            else:
                print("NOT in any reminder window")
                
            # Calculate next reminder window and when user will become eligible
            if time_since_checkin <= timedelta(hours=1.5):
                next_window = system_time + timedelta(hours=1.5)
                print(f"Next window (morning reminder) starts at: {next_window}")
                print(f"User will be eligible in: {next_window - now}")
            elif time_since_checkin <= timedelta(hours=3.5):
                next_window = system_time + timedelta(hours=3.5)
                print(f"Next window (mid-day check) starts at: {next_window}")
                print(f"User will be eligible in: {next_window - now}")
            elif time_since_checkin <= timedelta(hours=7.5):
                next_window = system_time + timedelta(hours=7.5)
                print(f"Next window (evening reset) starts at: {next_window}")
                print(f"User will be eligible in: {next_window - now}")
                
            # Calculate all upcoming windows
            print("\nAll upcoming reminder windows:")
            morning_window_start = system_time + timedelta(hours=1.5)
            morning_window_end = system_time + timedelta(hours=2.5)
            midday_window_start = system_time + timedelta(hours=3.5)
            midday_window_end = system_time + timedelta(hours=4.5)
            evening_window_start = system_time + timedelta(hours=7.5)
            evening_window_end = system_time + timedelta(hours=8.5)
            nextday_window_start = system_time + timedelta(hours=24)
            
            print(f"Morning window: {morning_window_start} to {morning_window_end}")
            print(f"Mid-day window: {midday_window_start} to {midday_window_end}")
            print(f"Evening window: {evening_window_start} to {evening_window_end}")
            print(f"Next-day window: starts at {nextday_window_start}")
    elif system_messages:
        latest_system_message = system_messages[0]
        latest_user_response = user_responses[0]
        
        system_time = latest_system_message['time']
        user_time = latest_user_response['time']
        
        if user_time > system_time:
            print("User has already responded to the latest check-in.")
            print(f"Latest system message: {system_time}")
            print(f"Latest user response: {user_time}")
        else:
            # User hasn't responded to the latest system message
            now = datetime.now(timezone.utc)
            time_since_checkin = now - system_time
            
            print(f"User hasn't responded to the latest check-in.")
            print(f"Latest system message: {system_time}")
            print(f"Latest user response: {user_time}")
            print(f"Time since check-in: {time_since_checkin}")
            
            # Check reminder windows
            if timedelta(hours=1.5) < time_since_checkin <= timedelta(hours=2.5):
                print("ELIGIBLE for first follow-up (morning reminder)")
                print(f"Morning window: {system_time + timedelta(hours=1.5)} to {system_time + timedelta(hours=2.5)}")
            elif timedelta(hours=3.5) < time_since_checkin <= timedelta(hours=4.5):
                print("ELIGIBLE for mid-day check")
                print(f"Mid-day window: {system_time + timedelta(hours=3.5)} to {system_time + timedelta(hours=4.5)}")
            elif timedelta(hours=7.5) < time_since_checkin <= timedelta(hours=8.5):
                print("ELIGIBLE for evening reset")
                print(f"Evening window: {system_time + timedelta(hours=7.5)} to {system_time + timedelta(hours=8.5)}")
            elif time_since_checkin > timedelta(hours=24):
                print("ELIGIBLE for next day support")
                print(f"Next day support: After {system_time + timedelta(hours=24)}")
            else:
                print("NOT in any reminder window")
                
            # Calculate next reminder window and when user will become eligible
            if time_since_checkin <= timedelta(hours=1.5):
                next_window = system_time + timedelta(hours=1.5)
                print(f"Next window (morning reminder) starts at: {next_window}")
                print(f"User will be eligible in: {next_window - now}")
            elif time_since_checkin <= timedelta(hours=3.5):
                next_window = system_time + timedelta(hours=3.5)
                print(f"Next window (mid-day check) starts at: {next_window}")
                print(f"User will be eligible in: {next_window - now}")
            elif time_since_checkin <= timedelta(hours=7.5):
                next_window = system_time + timedelta(hours=7.5)
                print(f"Next window (evening reset) starts at: {next_window}")
                print(f"User will be eligible in: {next_window - now}")
                
            # Calculate all upcoming windows
            print("\nAll upcoming reminder windows:")
            morning_window_start = system_time + timedelta(hours=1.5)
            morning_window_end = system_time + timedelta(hours=2.5)
            midday_window_start = system_time + timedelta(hours=3.5)
            midday_window_end = system_time + timedelta(hours=4.5)
            evening_window_start = system_time + timedelta(hours=7.5)
            evening_window_end = system_time + timedelta(hours=8.5)
            nextday_window_start = system_time + timedelta(hours=24)
            
            print(f"Morning window: {morning_window_start} to {morning_window_end}")
            print(f"Mid-day window: {midday_window_start} to {midday_window_end}")
            print(f"Evening window: {evening_window_start} to {evening_window_end}")
            print(f"Next-day window: starts at {nextday_window_start}")
                
except Exception as e:
    print(f"Error fetching responses: {str(e)}")
    import traceback
    traceback.print_exc() 