import firebase_admin
from firebase_admin import auth, credentials
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def set_admin_claim(email):
    # Initialize Firebase Admin SDK
    cred_path = os.getenv('FIREBASE_CREDENTIALS_PATH', './config/firebase-credentials.json')
    cred = credentials.Certificate(cred_path)
    
    try:
        firebase_admin.initialize_app(cred)
    except ValueError:
        # App already initialized
        pass
    
    try:
        # Get the user by email
        user = auth.get_user_by_email(email)
        
        # Set admin claim
        auth.set_custom_user_claims(user.uid, {'admin': True})
        
        print(f"Successfully set admin claim for user: {email}")
        
    except Exception as e:
        print(f"Error setting admin claim: {str(e)}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python set_admin.py <email>")
        sys.exit(1)
    
    email = sys.argv[1]
    set_admin_claim(email) 