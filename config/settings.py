import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Base configuration for the application"""
    # App Settings
    SECRET_KEY = os.environ.get('SECRET_KEY', 'default-secret-key')
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    # WhatsApp API Settings
    WHATSAPP_API_URL = os.environ.get('WHATSAPP_API_URL', 'https://graph.facebook.com/v17.0')
    WHATSAPP_VERIFY_TOKEN = os.environ.get('WHATSAPP_VERIFY_TOKEN', 'odinma_accountability_webhook')
    
    # Multiple WhatsApp accounts configuration
    # First account
    WHATSAPP_PHONE_NUMBER_ID_1 = os.environ.get('WHATSAPP_PHONE_NUMBER_ID_1')
    WHATSAPP_ACCESS_TOKEN_1 = os.environ.get('WHATSAPP_ACCESS_TOKEN_1')
    
    # Second account
    WHATSAPP_PHONE_NUMBER_ID_2 = os.environ.get('WHATSAPP_PHONE_NUMBER_ID_2')
    WHATSAPP_ACCESS_TOKEN_2 = os.environ.get('WHATSAPP_ACCESS_TOKEN_2')
    
    # Combine into lists for easier access
    WHATSAPP_PHONE_NUMBER_IDS = [
        WHATSAPP_PHONE_NUMBER_ID_1,
        WHATSAPP_PHONE_NUMBER_ID_2
    ]
    
    WHATSAPP_ACCESS_TOKENS = [
        WHATSAPP_ACCESS_TOKEN_1,
        WHATSAPP_ACCESS_TOKEN_2
    ]
    
    # For backward compatibility (single account usage)
    WHATSAPP_PHONE_NUMBER_ID = WHATSAPP_PHONE_NUMBER_ID_1
    WHATSAPP_ACCESS_TOKEN = WHATSAPP_ACCESS_TOKEN_1
    
    # Cron Job Settings (in UTC)
    DAILY_CHECKIN_TIME = os.environ.get('DAILY_CHECKIN_TIME', '08:00')  # 8 AM
    DAILY_TASK_TIME = os.environ.get('DAILY_TASK_TIME', '09:00')  # 9 AM
    WEEKLY_CHECKIN_TIME = os.environ.get('WEEKLY_CHECKIN_TIME', '09:00')  # 9 AM (Sunday)
    WEEKLY_CHECKIN_DAY = os.environ.get('WEEKLY_CHECKIN_DAY', '6')  # Sunday (0=Monday, 6=Sunday)
    
    # Cron security
    CRON_SECRET = os.environ.get('CRON_SECRET')
    
    # App Constants
    SENTIMENT_THRESHOLD_POSITIVE = float(os.environ.get('SENTIMENT_THRESHOLD_POSITIVE', '0.5'))
    SENTIMENT_THRESHOLD_NEGATIVE = float(os.environ.get('SENTIMENT_THRESHOLD_NEGATIVE', '-0.2'))
    
    # ADHD Hacks and Strategies
    ADHD_HACKS = [
        "Break the task into smaller, manageable chunks",
        "Set a timer for 25 minutes and focus only on this task",
        "Create a checklist for the steps needed",
        "Remove distractions from your environment",
        "Use the 'body doubling' technique - work alongside someone else",
        "Take a 5-minute break to move around",
        "Write down your thoughts to clear your mind",
        "Use the '2-minute rule' - if it takes less than 2 minutes, do it now",
        "Set up a reward for completing the task",
        "Visualize yourself completing the task successfully"
    ]

    # Firebase Admin SDK
    FIREBASE_CREDENTIALS = os.getenv('FIREBASE_CREDENTIALS_PATH', 'path/to/serviceAccountKey.json')
    
    # Firebase Web SDK
    FIREBASE_API_KEY = os.getenv('FIREBASE_API_KEY')
    FIREBASE_AUTH_DOMAIN = os.getenv('FIREBASE_AUTH_DOMAIN')
    FIREBASE_PROJECT_ID = os.getenv('FIREBASE_PROJECT_ID')
    FIREBASE_STORAGE_BUCKET = os.getenv('FIREBASE_STORAGE_BUCKET')
    FIREBASE_MESSAGING_SENDER_ID = os.getenv('FIREBASE_MESSAGING_SENDER_ID')
    FIREBASE_APP_ID = os.getenv('FIREBASE_APP_ID')
    
    # Session configuration
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = 86400  # 24 hours
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax' 