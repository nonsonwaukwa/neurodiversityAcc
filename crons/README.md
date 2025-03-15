# Cron Jobs for Neurodiversity Accountability System

This directory contains standalone Python scripts that can be scheduled as cron jobs on Railway.

## Available Cron Scripts

1. `daily_checkin_cron.py` - Sends daily morning check-ins to users at 8 AM UTC
2. `daily_tasks_cron.py` - Sends daily task reminders to users at 9 AM UTC  
3. `weekly_checkin_cron.py` - Sends weekly mental health check-ins on Sundays at 9 AM UTC

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