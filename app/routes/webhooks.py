from app.cron.reminders import handle_reminder_response

def handle_button_response(user, button_id):
    """Handle button responses from users"""
    
    # Reminder response handlers
    reminder_responses = [
        "plan_day", "quick_checkin", "remind_later",
        "plan_afternoon", "self_care", "just_chat",
        "share_day", "plan_tomorrow", "rest_now",
        "fresh_start", "gentle_checkin", "need_help",
        "simplify_tasks", "just_talk", "get_strategies",
        "rest_and_recharge", "tiny_step", "celebrate",
        "need_support", "adjust_tasks", "explore_options"
    ]
    
    if button_id in reminder_responses:
        handle_reminder_response(user, button_id)
        return

    # ... existing button handlers ... 