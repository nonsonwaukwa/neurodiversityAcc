import logging
from datetime import datetime
from app.models.user import User
from app.models.checkin import CheckIn
from app.services.whatsapp import get_whatsapp_service
from app.services.progress_report import get_progress_service
import traceback

logger = logging.getLogger(__name__)

def send_weekly_progress_reports():
    """Send weekly progress reports to all users on Saturdays"""
    logger.info("Running weekly progress report cron job")
    
    try:
        # Only run on Saturdays (weekday 5)
        if datetime.now().weekday() != 5:
            logger.info("Not Saturday, skipping weekly progress reports")
            return
        
        # Get all active users
        users = User.get_all_active()
        
        if not users:
            logger.info("No active users found for weekly progress reports")
            return
        
        # Group users by account
        users_by_account = {}
        for user in users:
            account_index = user.account_index
            if account_index not in users_by_account:
                users_by_account[account_index] = []
            users_by_account[account_index].append(user)
        
        progress_service = get_progress_service()
        
        # Process each account
        for account_index, account_users in users_by_account.items():
            # Get the WhatsApp service for this account
            whatsapp_service = get_whatsapp_service(account_index)
            
            # Process each user in this account
            for user in account_users:
                try:
                    _send_user_progress_report(user, whatsapp_service, progress_service)
                except Exception as e:
                    logger.error(f"Error sending progress report to user {user.user_id}: {e}")
                    logger.debug(traceback.format_exc())

    except ImportError as e:
        # Handle missing dependencies gracefully
        logger.error(f"Missing dependency when running weekly progress reports: {e}")
        logger.error("Please install the optional dependencies listed in requirements.txt")
    except Exception as e:
        logger.error(f"Unexpected error in weekly progress reports: {e}")
        logger.debug(traceback.format_exc())

def _send_user_progress_report(user, whatsapp_service, progress_service):
    """
    Send a progress report to a specific user
    
    Args:
        user (User): The user to send the report to
        whatsapp_service (WhatsAppService): The WhatsApp service instance
        progress_service (ProgressReportService): The progress report service instance
    """
    # Generate report for this user
    report = progress_service.generate_weekly_report(user.user_id)
    
    if not report:
        logger.error(f"Failed to generate progress report for user {user.user_id}")
        return
    
    # Send appropriate message based on report type
    if report['type'] == 'success':
        # Success report - celebrate achievements
        whatsapp_service.send_message(user.user_id, report['message'])
        
        # Create check-in record
        CheckIn.create(
            user.user_id, 
            "Weekly Celebration sent", 
            CheckIn.TYPE_WEEKLY
        )
        
        logger.info(f"Sent achievement celebration to user {user.user_id}")
        
    elif report['type'] == 'compassion':
        # Compassionate check-in for users who struggled
        whatsapp_service.send_message(user.user_id, report['message'])
        
        # Create check-in record
        CheckIn.create(
            user.user_id, 
            "Compassion check-in sent", 
            CheckIn.TYPE_WEEKLY
        )
        
        logger.info(f"Sent compassion check-in to user {user.user_id}")

def process_win_reflection(user_id, reflection_text):
    """
    Process a user's reflection on their strategies or small wins
    
    Args:
        user_id (str): The user's ID
        reflection_text (str): The user's reflection text
        
    Returns:
        str: Response message
    """
    try:
        user = User.get(user_id)
        if not user:
            logger.error(f"User {user_id} not found for strategy reflection")
            return "Thank you for sharing!"
        
        progress_service = get_progress_service()
        response = progress_service.process_win_reflection(user, reflection_text)
        
        # Create check-in record for the reflection
        CheckIn.create(
            user.user_id, 
            f"Strategy reflection: {reflection_text}", 
            CheckIn.TYPE_WEEKLY
        )
        
        return response
    except Exception as e:
        logger.error(f"Error processing strategy reflection: {e}")
        logger.debug(traceback.format_exc())
        return "Thank you for sharing! Your insights are valuable." 