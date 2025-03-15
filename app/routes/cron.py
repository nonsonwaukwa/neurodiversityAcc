from flask import Blueprint, request, jsonify, current_app
from app.cron.daily_checkin import send_daily_checkin
from app.cron.daily_tasks import send_daily_tasks
from app.cron.weekly_checkin import send_weekly_checkin
import os
import logging

# Set up logger
logger = logging.getLogger(__name__)

# Create blueprint
cron_bp = Blueprint('cron', __name__)

def verify_cron_secret():
    """Verify that the cron secret is correct."""
    cron_secret = os.environ.get('CRON_SECRET')
    if not cron_secret:
        logger.error("CRON_SECRET environment variable not set")
        return False
    
    request_secret = request.headers.get('X-Cron-Secret')
    if not request_secret:
        logger.error("Missing X-Cron-Secret header")
        return False
    
    return request_secret == cron_secret

@cron_bp.route('/cron/daily-checkin', methods=['POST'])
def daily_checkin_webhook():
    """Handle the daily check-in cron job webhook."""
    logger.info("Received daily check-in webhook request")
    
    # Verify the cron secret
    if not verify_cron_secret():
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        # Run the daily check-in
        send_daily_checkin()
        return jsonify({"status": "success", "message": "Daily check-in completed"}), 200
    except Exception as e:
        logger.error(f"Error in daily check-in webhook: {str(e)}")
        return jsonify({"error": str(e)}), 500

@cron_bp.route('/cron/daily-tasks', methods=['POST'])
def daily_tasks_webhook():
    """Handle the daily tasks cron job webhook."""
    logger.info("Received daily tasks webhook request")
    
    # Verify the cron secret
    if not verify_cron_secret():
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        # Run the daily tasks
        send_daily_tasks()
        return jsonify({"status": "success", "message": "Daily tasks completed"}), 200
    except Exception as e:
        logger.error(f"Error in daily tasks webhook: {str(e)}")
        return jsonify({"error": str(e)}), 500

@cron_bp.route('/cron/weekly-checkin', methods=['POST'])
def weekly_checkin_webhook():
    """Handle the weekly check-in cron job webhook."""
    logger.info("Received weekly check-in webhook request")
    
    # Verify the cron secret
    if not verify_cron_secret():
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        # Run the weekly check-in
        send_weekly_checkin()
        return jsonify({"status": "success", "message": "Weekly check-in completed"}), 200
    except Exception as e:
        logger.error(f"Error in weekly check-in webhook: {str(e)}")
        return jsonify({"error": str(e)}), 500 