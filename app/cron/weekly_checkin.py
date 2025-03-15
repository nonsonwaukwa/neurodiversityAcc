from app.models.user import User
from app.services.whatsapp import get_whatsapp_service
import logging

# Set up logger
logger = logging.getLogger(__name__)

def send_weekly_checkin():
    """Send weekly mental check-in messages to all users from both accounts"""
    logger.info("Running weekly check-in cron job")
    
    # Get all users
    users = User.get_all()
    
    if not users:
        logger.info("No users found for weekly check-in")
        return
    
    # Group users by account
    users_by_account = {}
    for user in users:
        account_index = user.account_index
        if account_index not in users_by_account:
            users_by_account[account_index] = []
        users_by_account[account_index].append(user)
    
    # Process each account
    for account_index, account_users in users_by_account.items():
        # Get the WhatsApp service for this account
        whatsapp_service = get_whatsapp_service(account_index)
        
        # Process each user in this account
        for user in account_users:
            try:
                # Format the message with the user's name
                name = user.name.split('_')[0] if '_' in user.name else user.name
                checkin_message = f"Hey {name}, let's check in! How are you feeling about the upcoming week?"
                
                logger.info(f"Sending weekly check-in to user {user.user_id} (account {account_index})")
                response = whatsapp_service.send_message(user.user_id, checkin_message)
                
                if response:
                    logger.info(f"Successfully sent weekly check-in to user {user.user_id}")
                else:
                    logger.error(f"Failed to send weekly check-in to user {user.user_id}")
            
            except Exception as e:
                logger.error(f"Error sending weekly check-in to user {user.user_id}: {e}") 