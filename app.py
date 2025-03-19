# Register cron jobs
@app.cli.command('run-daily-checkin')
def run_daily_checkin():
    """Run the daily check-in cron job"""
    try:
        from app.cron.daily_checkin import send_daily_checkin
        send_daily_checkin()
    except ImportError as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Missing dependency for daily check-in: {e}")
        logger.error("Please install the optional dependencies listed in requirements.txt")

@app.cli.command('run-weekly-checkin')
def run_weekly_checkin():
    """Run the weekly check-in cron job"""
    try:
        from app.cron.weekly_checkin import send_weekly_checkin
        send_weekly_checkin()
    except ImportError as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Missing dependency for weekly check-in: {e}")
        logger.error("Please install the optional dependencies listed in requirements.txt")

@app.cli.command('run-daily-reminders')
def run_daily_reminders():
    """Run the daily task reminders cron job"""
    try:
        from app.cron.daily_checkin import send_daily_reminders
        send_daily_reminders()
    except ImportError as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Missing dependency for daily reminders: {e}")
        logger.error("Please install the optional dependencies listed in requirements.txt")

@app.cli.command('run-follow-up-reminders')
def run_follow_up_reminders():
    """Run the follow-up reminders cron job"""
    try:
        from app.cron.reminders import send_checkin_reminders
        send_checkin_reminders()
    except ImportError as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Missing dependency for follow-up reminders: {e}")
        logger.error("Please install the optional dependencies listed in requirements.txt")

@app.cli.command("run-weekly-progress-reports")
def run_weekly_progress_reports():
    """Run weekly progress reports for all users"""
    try:
        from app.cron.weekly_report import send_weekly_progress_reports
        send_weekly_progress_reports()
    except ImportError as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Missing dependency for weekly progress reports: {e}")
        logger.error("Please install the optional dependencies listed in requirements.txt")

@app.cli.command('run-followup-reminders')
def run_followup_reminders():
    """Run the follow-up reminders cron job"""
    try:
        from app.cron.reminders import send_checkin_reminders
        send_checkin_reminders()
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error running follow-up reminders: {e}") 