import os
import sys

# Add the project root directory to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Import and run the daily check-in
from app.cron.daily_checkin import send_daily_checkin

if __name__ == "__main__":
    send_daily_checkin() 