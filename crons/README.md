# Cron Jobs for Neurodiversity Accountability System

This directory contains standalone Python scripts that can be scheduled as cron jobs on Railway.

## Available Cron Scripts

1. `daily_checkin_cron.py` - Sends daily morning check-ins to users at 8 AM UTC
2. `daily_tasks_cron.py` - Sends daily task reminders to users at 9 AM UTC  
3. `weekly_checkin_cron.py` - Sends weekly mental health check-ins on Sundays at 9 AM UTC
4. `morning_followup_cron.py` - Sends follow-up reminders 2 hours after check-in (12:30 PM)
5. `midday_followup_cron.py` - Sends follow-up reminders 4 hours after check-in (2:30 PM)
6. `evening_followup_cron.py` - Sends follow-up reminders 8 hours after check-in (6:30 PM)

## Setting Up Cron Jobs on Railway

1. Deploy your main application to Railway
2. Get your application URL (e.g., `https://your-app-name.railway.app`)
3. For each cron job, create a new Railway service:
   - Select "Cron Job" as the service type
   - Set the cron schedule expression (see examples below)
   - Set the required environment variables:
     - `APP_URL` - Your application URL (e.g., `https://your-app-name.railway.app`)
     - `CRON_SECRET` - The same secret value as set in your main application
   - Add the command to run the script, for example:
     - `python crons/daily_checkin_cron.py`

## Cron Schedule Examples

- Daily Check-in (8 AM UTC): `0 8 * * *`
- Daily Tasks (9 AM UTC): `0 9 * * *`
- Weekly Check-in (Sunday 9 AM UTC): `0 9 * * 0`
- Morning Follow-up Reminders (12:30 PM UTC): `30 12 * * *`
- Mid-day Follow-up Reminders (2:30 PM UTC): `30 14 * * *`
- Evening Follow-up Reminders (6:30 PM UTC): `30 18 * * *`

## Important Notes for Follow-up Reminders

The follow-up reminders are designed to be neurodivergent-friendly and will only be sent to users who haven't yet responded to their daily check-ins. Each reminder provides different options appropriate to the time of day.

- **Morning Follow-up (12:30 PM)**: Gentle nudge with day planning options
- **Mid-day Follow-up (2:30 PM)**: Options for afternoon planning or self-care
- **Evening Follow-up (6:30 PM)**: Evening reset with self-care tips and next-day planning

Each reminder script automatically checks if a user has already responded to avoid sending unnecessary reminders.

## Security

These scripts use a secret token (`CRON_SECRET`) to authenticate with the main application. This prevents unauthorized access to your cron endpoints. Make sure to set the same `CRON_SECRET` value in:

1. Your main application's environment variables
2. Each of your cron job service's environment variables

## Testing

You can test these cron scripts locally by setting the required environment variables and running them:

```bash
export APP_URL=http://localhost:5000
export CRON_SECRET=your-secure-random-string
python crons/daily_checkin_cron.py
``` 