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
        "Break your task into smaller steps - what's the first tiny step?",
        "Try the 5-minute rule - commit to just 5 minutes, then decide if you want to continue",
        "Body doubling: Find someone to work alongside you (even virtually)",
        "Pomodoro technique: 25 minutes work, 5 minutes break",
        "Change your environment - move to a different room or location",
        "Use noise-cancelling headphones or background music without lyrics",
        "Set a timer with a specific deadline",
        "Reward yourself after task completion",
        "Use the 'if-then' method - tie your task to an existing habit",
        "Eliminate distractions: put your phone in another room",
        "Visualize your success and how you'll feel after completion",
        "Try standing or walking while working on this task"
    ] 