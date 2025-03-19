# Neurodiversity Accountability System

A WhatsApp-based accountability system designed to help neurodivergent individuals manage their daily tasks and track their mental well-being.

## Features

- **Multiple WhatsApp Account Support**: Connect to two WhatsApp Business API accounts simultaneously
- **Daily Check-ins**: Automated morning check-ins to gauge user sentiment
- **Task Management**: Personalized task management and reminders
- **Weekly Mental Health Check-ins**: Regular monitoring of users' mental well-being
- **Adaptive Responses**: System responses adapt based on user sentiment
- **Custom ADHD Strategies**: Provides tailored strategies to help overcome executive dysfunction
- **Voice Note Support**: Submit check-ins and updates via voice notes, which are automatically transcribed and processed, enhancing accessibility for neurodivergent users

## System Architecture

- **Backend**: Flask-based API
- **Messaging**: WhatsApp Business API integration (supports multiple accounts)
- **Database**: Firebase Firestore for storing user data, tasks, and check-ins
- **Scheduling**: Standalone cron scripts for Railway deployment
- **Authentication**: Secure endpoints with token-based authentication

## Setup and Deployment

### Prerequisites

1. Two WhatsApp Business API accounts set up through the Meta Developer Portal
2. A Firebase project with Firestore database
3. A Railway account for deployment
4. Git for version control

### Firebase Setup

1. Create a Firebase project at [https://console.firebase.google.com/](https://console.firebase.google.com/)
2. Set up Firestore Database in your project
3. Go to Project Settings > Service Accounts
4. Click "Generate new private key" to download the Firebase credentials JSON file
5. You'll use this file for local development and deployment

### Local Development Setup

1. Clone the repository:
   ```bash
   git clone [repository-url]
   cd neurodiversityAcc
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Create a `.env` file based on `.env.sample`:
   ```bash
   cp .env.sample .env
   ```

4. Modify the `.env` file with your own values, including:
   - WhatsApp API credentials for both accounts
   - Firebase configuration (either path to credentials file or the JSON content)
   - Security keys and tokens

5. Test your Firebase connection:
   ```bash
   python firebase_test.py
   ```

6. Run the application:
   ```bash
   flask run
   ```

### Deploying to Railway

#### Main Application Deployment

1. Create a Railway account and install the Railway CLI (optional):
   ```bash
   npm i -g @railway/cli
   ```

2. Create a new project on Railway through the web dashboard

3. Link your GitHub repository or push your code to Railway directly

4. Set the following environment variables in the Railway dashboard:
   - `FLASK_APP=main.py`
   - `FLASK_DEBUG=False`
   - `PORT=5000`
   - `SECRET_KEY=your-secure-key`
   - `WHATSAPP_PHONE_NUMBER_ID_1=your-first-account-id`
   - `WHATSAPP_ACCESS_TOKEN_1=your-first-account-token`
   - `WHATSAPP_PHONE_NUMBER_ID_2=your-second-account-id`
   - `WHATSAPP_ACCESS_TOKEN_2=your-second-account-token`
   - `CRON_SECRET=your-secure-random-string`
   - `FIREBASE_CREDENTIALS=your-firebase-credentials-json` (paste the entire JSON)

5. Set the following deployment settings:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn main:app`

6. Deploy the application and note the URL (e.g., `https://your-app-name.railway.app`)

#### Setting Up Cron Jobs on Railway

For each cron job, create a separate Railway service:

1. **Daily Check-in Cron (8 AM UTC)**
   - Create a new Railway service
   - Choose "Cron Job" as the service type
   - Schedule: `0 8 * * *`
   - Command: `python crons/daily_checkin_cron.py`
   - Environment Variables:
     - `APP_URL=https://your-app-name.railway.app`
     - `CRON_SECRET=your-secure-random-string` (same as main app)

2. **Daily Tasks Cron (9 AM UTC)**
   - Create a new Railway service
   - Choose "Cron Job" as the service type
   - Schedule: `0 9 * * *`
   - Command: `python crons/daily_tasks_cron.py`
   - Environment Variables:
     - `APP_URL=https://your-app-name.railway.app`
     - `CRON_SECRET=your-secure-random-string` (same as main app)

3. **Weekly Check-in Cron (Sunday 9 AM UTC)**
   - Create a new Railway service
   - Choose "Cron Job" as the service type
   - Schedule: `0 9 * * 0`
   - Command: `python crons/weekly_checkin_cron.py`
   - Environment Variables:
     - `APP_URL=https://your-app-name.railway.app`
     - `CRON_SECRET=your-secure-random-string` (same as main app)

### Configuring WhatsApp Business API Webhook

1. Go to your Meta Developer Portal
2. For each WhatsApp Business account:
   - Navigate to your app
   - Go to WhatsApp > Configuration
   - Set the Callback URL to `https://your-app-name.railway.app/api/webhook`
   - Set the Verify Token to match your `WHATSAPP_VERIFY_TOKEN` environment variable
   - Add the following webhooks: messages, message_status_updates

## Testing

### Testing Locally

1. Set up ngrok or a similar tool to expose your local server:
   ```bash
   ngrok http 5000
   ```

2. Update your webhook URL in the Meta Developer Portal to your ngrok URL

3. To test cron jobs locally, set the required environment variables and run the scripts:
   ```bash
   export APP_URL=http://localhost:5000
   export CRON_SECRET=your-secure-random-string
   python crons/daily_checkin_cron.py
   ```

### Testing in Production

1. Monitor Railway logs for any errors
2. Use Railway's built-in metrics to track application performance
3. Send test messages to the WhatsApp number to ensure the webhook is working

## Troubleshooting

- **WhatsApp Webhook Not Receiving Messages**:
  - Verify webhook URL is correctly set in Meta Developer Portal
  - Check that verify token matches your environment variable
  - Ensure proper webhooks are subscribed (messages, message_status_updates)

- **Cron Jobs Not Running**:
  - Verify environment variables are correctly set in Railway
  - Check Railway logs for any execution errors
  - Ensure the cron expression format is correct

- **Firebase Connection Issues**:
  - Check that the FIREBASE_CREDENTIALS environment variable contains valid JSON
  - Verify that the service account has the correct permissions
  - For local testing, ensure the credentials file exists at the specified path

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit your changes: `git commit -m 'Add some feature'`
4. Push to the branch: `git push origin feature-name`
5. Submit a pull request 