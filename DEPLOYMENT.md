# Railway Deployment Guide

This guide covers deploying the Neurodiversity Accountability System on Railway with support for multiple WhatsApp accounts.

## Overview of the Deployment Architecture

The system is designed with the following components:

1. **Main Application Service**: Flask backend that handles webhooks and API endpoints
2. **Separate Cron Services**: Individual cron jobs for daily check-ins, daily tasks, and weekly check-ins

## Steps for Railway Deployment

### 1. Prepare Your Environment Variables

Before deploying, you need to have access to:
- WhatsApp Business API credentials for 2 accounts
- A secure random string for your CRON_SECRET
- Firebase configuration (service account credentials)

### 2. Deploy the Main Application

1. **Create a new project on Railway**:
   - Log in to your Railway account
   - Click "New Project" and select "Deploy from GitHub repo"
   - Connect your GitHub account and select your repository
   - Alternatively, you can use "Deploy from template" if you've created a template

2. **Configure environment variables**:
   - Click on your deployed service
   - Go to the "Variables" tab
   - Add the following variables:
     ```
     FLASK_APP=main.py
     FLASK_DEBUG=False
     PORT=5000
     SECRET_KEY=your-secure-key
     
     # WhatsApp API Settings - Account 1
     WHATSAPP_PHONE_NUMBER_ID_1=your-first-account-id
     WHATSAPP_ACCESS_TOKEN_1=your-first-account-token
     WHATSAPP_VERIFY_TOKEN=your-verification-token
     
     # WhatsApp API Settings - Account 2
     WHATSAPP_PHONE_NUMBER_ID_2=your-second-account-id
     WHATSAPP_ACCESS_TOKEN_2=your-second-account-token
     
     # Firebase Configuration (Either use FIREBASE_CREDENTIALS or FIREBASE_CREDENTIALS_PATH)
     # Option 1: Paste your Firebase credentials JSON directly
     FIREBASE_CREDENTIALS={"type":"service_account","project_id":"your-project-id",...rest of credentials}
     
     # Option 2: Upload your Firebase credentials file to Railway and provide the path
     # FIREBASE_CREDENTIALS_PATH=./firebase-credentials.json
     
     # Cron Security
     CRON_SECRET=your-secure-random-string
     ```

3. **Configure deployment settings**:
   - Go to the "Settings" tab
   - Set the following:
     - Root Directory: `/` (or the directory containing your app)
     - Build Command: `pip install -r requirements.txt`
     - Start Command: `gunicorn main:app`
     - Watch Paths: `**/*.py`
     - Health Check Path: `/health`

4. **Deploy the application**:
   - The deployment should start automatically after configuration
   - Once deployed, copy your application URL (e.g., `https://your-app.railway.app`)

### 3. Set Up Cron Jobs as Separate Services

For each cron job, follow these steps:

#### Daily Check-in Cron (8 AM UTC)

1. **Create a new Railway service in the same project**:
   - Click "New Service" in your Railway project
   - Select "Cron Service" as the type

2. **Configure the cron job**:
   - Schedule: `0 8 * * *` (Runs at 8 AM UTC daily)
   - Command: `python crons/daily_checkin_cron.py`

3. **Set environment variables**:
   - `APP_URL=https://your-app.railway.app` (URL from step 2.4)
   - `CRON_SECRET=your-secure-random-string` (same as in the main app)

#### Daily Tasks Cron (9 AM UTC)

1. **Create a new Railway service**:
   - Click "New Service" in your Railway project
   - Select "Cron Service" as the type

2. **Configure the cron job**:
   - Schedule: `0 9 * * *` (Runs at 9 AM UTC daily)
   - Command: `python crons/daily_tasks_cron.py`

3. **Set environment variables**:
   - `APP_URL=https://your-app.railway.app`
   - `CRON_SECRET=your-secure-random-string`

#### Weekly Check-in Cron (Sunday 9 AM UTC)

1. **Create a new Railway service**:
   - Click "New Service" in your Railway project
   - Select "Cron Service" as the type

2. **Configure the cron job**:
   - Schedule: `0 9 * * 0` (Runs at 9 AM UTC every Sunday)
   - Command: `python crons/weekly_checkin_cron.py`

3. **Set environment variables**:
   - `APP_URL=https://your-app.railway.app`
   - `CRON_SECRET=your-secure-random-string`

### 4. Configure WhatsApp Business API Webhooks

For each WhatsApp Business account:

1. **Go to Meta Developer Portal**:
   - Navigate to your app
   - Select "WhatsApp" from the products menu
   - Go to "Configuration"

2. **Set up webhook**:
   - Callback URL: `https://your-app.railway.app/api/webhook`
   - Verify Token: The same as your `WHATSAPP_VERIFY_TOKEN` environment variable
   - Subscribe to:
     - messages
     - message_status_updates

3. **Test the webhook**:
   - Click "Verify and Save"
   - Send a test message to one of your WhatsApp test numbers

### 5. Monitor and Troubleshoot

1. **View application logs**:
   - Go to the "Logs" tab in your main application service
   - Look for any error messages or issues

2. **Monitor cron job executions**:
   - Each cron job service will have its own logs
   - Check that they're executing at the scheduled times

3. **Common issues**:
   - If webhooks aren't working, verify URL and verify token
   - If cron jobs aren't triggering, check environment variables and logs
   - If the application crashes, check the logs for error messages
   - If Firebase authentication fails, verify your credentials are correct and properly formatted

## Updating Your Deployment

1. **Push changes to your repository**:
   - Railway will automatically detect the changes
   - A new deployment will be triggered

2. **Manual redeployment**:
   - Go to your service dashboard
   - Click the "Deploy" button to trigger a new deployment

## Additional Railway Features to Consider

1. **Custom Domains**:
   - Click on "Settings" in your main service
   - Go to "Domains" and add your custom domain

2. **Environment Groups**:
   - Create environment groups to share variables between services
   - This is useful for secrets like the CRON_SECRET

3. **Metrics**:
   - Monitor CPU, memory, and disk usage from the "Metrics" tab
   - Set up alerts for high usage

## Scaling Considerations

- Railway automatically scales your application based on demand
- For higher traffic, you may need to increase resources in the service settings
- Each cron job runs in its own isolated environment, ensuring reliability 