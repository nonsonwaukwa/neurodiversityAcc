from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import pytz
import logging

# Set up logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Scheduler instance
scheduler = None

def init_scheduler(app):
    """
    Initialize the scheduler for cron jobs
    
    Args:
        app: The Flask application
        
    Returns:
        BackgroundScheduler: The scheduler instance
    """
    global scheduler
    
    # Create scheduler
    scheduler = BackgroundScheduler()
    
    with app.app_context():
        # Import cron jobs
        from app.cron.daily_checkin import schedule_daily_checkin
        from app.cron.daily_tasks import schedule_daily_tasks
        from app.cron.weekly_checkin import schedule_weekly_checkin
        
        # Schedule jobs
        schedule_daily_checkin(scheduler)
        schedule_daily_tasks(scheduler)
        schedule_weekly_checkin(scheduler)
        
        # Start the scheduler
        if not scheduler.running:
            scheduler.start()
            logger.info("Scheduler started")
    
    return scheduler

def shutdown_scheduler():
    """Shut down the scheduler"""
    global scheduler
    if scheduler and scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler shut down") 