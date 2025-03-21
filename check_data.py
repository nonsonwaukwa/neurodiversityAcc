from app.models.user import User
from app.models.checkin import CheckIn
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

print('User instances:')
users = User.get_all()
print(f'Found {len(users)} users')

for user in users:
    print(f'User ID: {user.user_id}, Planning type: {user.planning_type}')

print('\nCheck-in data:')
for user in users:
    try:
        # Get check-ins directly from Firestore to avoid the model error
        from config.firebase_config import get_db
        db = get_db()
        
        query = db.collection('checkins')\
            .where('user_id', '==', user.user_id)\
            .order_by('created_at', direction="DESCENDING")\
            .limit(5)
            
        checkins = list(query.stream())
        print(f'Found {len(checkins)} check-ins for user {user.user_id}')
        
        for i, doc in enumerate(checkins):
            data = doc.to_dict()
            created_at = data.get('created_at')
            if created_at:
                # Extract the timestamp without trying to access datetime attribute
                timestamp_str = str(created_at)
            else:
                timestamp_str = "None"
                
            print(f"  Check-in {i+1}: ID: {doc.id}")
            print(f"    Time: {timestamp_str}")
            print(f"    Response: {data.get('response')}")
            print(f"    Sentiment score: {data.get('sentiment_score')}")
            print(f"    Is response: {data.get('is_response')}")
            print(f"    Needs follow-up: {data.get('needs_followup', 'Not set')}")
            
    except Exception as e:
        print(f"Error retrieving check-ins for user {user.user_id}: {str(e)}")
        import traceback
        traceback.print_exc() 