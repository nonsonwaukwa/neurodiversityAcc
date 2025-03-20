# Reminder Cron System Guide

This guide explains how to use and test the reminder cron system before pushing to production.

## Overview

The reminder system checks for users who have not responded to check-ins and sends them follow-up messages at appropriate intervals:

- **Morning Reminder**: 1.5-2.5 hours after check-in
- **Mid-day Check**: 3.5-4.5 hours after check-in
- **Evening Reset**: 7.5-8.5 hours after check-in
- **Next Day Support**: >24 hours after check-in

## Prerequisites

1. Make sure your `.env` file has the following settings:
   ```
   # WhatsApp API Configuration
   WHATSAPP_API_URL=https://graph.facebook.com/v17.0
   WHATSAPP_PHONE_ID_0=<your-phone-id>
   WHATSAPP_ACCESS_TOKEN_0=<your-access-token>
   
   # Cron Settings
   ENABLE_CRON=True
   CRON_SECRET=<your-secret>
   
   # Cron Schedules
   MORNING_FOLLOWUP_CRON=0 12 * * *
   MIDDAY_FOLLOWUP_CRON=0 14 * * *
   EVENING_FOLLOWUP_CRON=0 18 * * *
   ```

2. Ensure your Firestore database has the required indexes (automatically deployed from `firestore.indexes.json`).

## Testing Locally

### 1. Using the Cron Runner Script

The easiest way to test is with our `cron_runner.py` script:

```bash
# Run the appropriate reminder type based on time of day
python cron_runner.py --auto

# Test specific reminder types
python cron_runner.py --morning
python cron_runner.py --midday
python cron_runner.py --evening
python cron_runner.py --nextday

# Test all reminder types
python cron_runner.py --all
```

### 2. Using cURL (for direct API testing)

```bash
# Replace YOUR_CRON_SECRET with your actual cron secret
curl -X POST http://localhost:5000/api/cron/followup-reminders \
  -H "X-Cron-Secret: YOUR_CRON_SECRET" \
  -H "Content-Type: application/json" \
  -d '{"reminder_type": "morning"}'
```

## Deployment to Railway

The project uses standalone cron scripts in the `crons` directory which can be executed directly by Railway's cron service.

### Option 1: Using Standalone Cron Scripts (Recommended)

Create separate Railway cron services for each reminder type:

1. **Morning Follow-up Cron**:
   - Cron Schedule: `0 12 * * *` (12 PM UTC daily)
   - Command: `python crons/morning_followup_cron.py`
   - Required Environment Variables:
     - `APP_URL`: The base URL of your deployed app
     - `CRON_SECRET`: Secret for webhook authentication

2. **Mid-day Follow-up Cron**:
   - Cron Schedule: `0 14 * * *` (2 PM UTC daily)
   - Command: `python crons/midday_followup_cron.py`
   - Required Environment Variables: Same as above

3. **Evening Follow-up Cron**:
   - Cron Schedule: `0 18 * * *` (6 PM UTC daily)
   - Command: `python crons/evening_followup_cron.py`
   - Required Environment Variables: Same as above

4. **Next-day Follow-up Cron**:
   - Cron Schedule: `0 9 * * *` (9 AM UTC daily)
   - Command: `python crons/nextday_followup_cron.py`
   - Required Environment Variables: Same as above

### Option 2: Using Direct Webhook Calls

Alternatively, you can use webhook calls (less recommended):

1. **Morning Reminder Cron**:
   - Cron Schedule: `0 12 * * *` (12 PM UTC daily)
   - Command: `curl -X POST ${{SERVICE_URL}}/api/cron/followup-reminders -H "X-Cron-Secret: ${{CRON_SECRET}}" -H "Content-Type: application/json" -d '{"reminder_type": "morning"}'`

2. **Mid-day Reminder Cron**:
   - Cron Schedule: `0 14 * * *` (2 PM UTC daily)
   - Command: `curl -X POST ${{SERVICE_URL}}/api/cron/followup-reminders -H "X-Cron-Secret: ${{CRON_SECRET}}" -H "Content-Type: application/json" -d '{"reminder_type": "midday"}'`

3. **Evening Reminder Cron**:
   - Cron Schedule: `0 18 * * *` (6 PM UTC daily)
   - Command: `curl -X POST ${{SERVICE_URL}}/api/cron/followup-reminders -H "X-Cron-Secret: ${{CRON_SECRET}}" -H "Content-Type: application/json" -d '{"reminder_type": "evening"}'`

4. **Next Day Reminder Cron**:
   - Cron Schedule: `0 9 * * *` (9 AM UTC daily)
   - Command: `curl -X POST ${{SERVICE_URL}}/api/cron/followup-reminders -H "X-Cron-Secret: ${{CRON_SECRET}}" -H "Content-Type: application/json" -d '{"reminder_type": "nextday"}'`

## Troubleshooting

If reminders aren't being sent:

1. Check the logs for error messages
2. Verify your WhatsApp API credentials
3. Make sure `ENABLE_CRON` is set to `True`
4. Confirm that Firestore indexes are created (use `setup_firestore_indexes.py`)
5. Verify that users have check-ins but no responses
6. Test with the direct reminder tool:
   ```bash
   python send_direct_reminder.py 2348023672476 nextday
   ```
7. Check if the standalone cron scripts are configured with the right environment variables:
   - `APP_URL`: The base URL of your app (e.g., `https://your-app.railway.app`)
   - `CRON_SECRET`: Must match the `CRON_SECRET` in your app's environment

## Reminder Logic

The reminder system uses these checks to determine eligibility:

```python
# First Follow-up (Morning)
if timedelta(hours=1.5) < time_since_checkin <= timedelta(hours=2.5):
    # Send morning reminder
    
# Mid-day Check
elif timedelta(hours=3.5) < time_since_checkin <= timedelta(hours=4.5):
    # Send mid-day reminder
    
# Evening Reset
elif timedelta(hours=7.5) < time_since_checkin <= timedelta(hours=8.5):
    # Send evening reminder

# Next Day Support (if more than 24 hours)
elif time_since_checkin > timedelta(hours=24):
    # Send next-day support message
``` 