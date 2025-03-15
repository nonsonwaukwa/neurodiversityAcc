#!/bin/bash
# Script to deploy the Neurodiversity Accountability System to Railway

echo "=== Deploying Neurodiversity Accountability System to Railway ==="
echo ""
echo "Prerequisites:"
echo "1. You should have the Railway CLI installed (https://docs.railway.app/develop/cli)"
echo "2. You should be logged in to Railway (railway login)"
echo "3. You should have a Railway project created (railway init)"
echo ""

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null
then
    echo "Railway CLI is not installed. Please install it first:"
    echo "npm i -g @railway/cli"
    exit 1
fi

# Check if logged in to Railway
if ! railway whoami &> /dev/null
then
    echo "Not logged in to Railway. Please login first:"
    echo "railway login"
    exit 1
fi

echo "Setting up environment variables..."
echo "This will set up your WhatsApp credentials and Firebase configuration in Railway."

# Prompt for confirmation
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    echo "Deployment cancelled."
    exit 1
fi

# Set environment variables in Railway
echo "Setting environment variables in Railway..."
railway variables set \
    FLASK_APP=main.py \
    FLASK_DEBUG=False \
    PORT=5000 \
    ENABLE_CRON=True \
    DAILY_CHECKIN_TIME=08:00 \
    DAILY_TASK_TIME=09:00 \
    WEEKLY_CHECKIN_TIME=09:00 \
    WEEKLY_CHECKIN_DAY=6 \
    SENTIMENT_THRESHOLD_POSITIVE=0.5 \
    SENTIMENT_THRESHOLD_NEGATIVE=-0.2

echo ""
echo "Please manually set the following sensitive environment variables in Railway:"
echo "1. SECRET_KEY"
echo "2. WHATSAPP_PHONE_NUMBER_ID_1 and WHATSAPP_PHONE_NUMBER_ID_2"
echo "3. WHATSAPP_ACCESS_TOKEN_1 and WHATSAPP_ACCESS_TOKEN_2"
echo "4. WHATSAPP_VERIFY_TOKEN"
echo "5. FIREBASE_CREDENTIALS (as a JSON string)"
echo ""

# Deploy to Railway
echo "Deploying to Railway..."
railway up

echo ""
echo "Deployment complete!"
echo ""

# Get the deployment URL
DEPLOY_URL=$(railway status | grep "Deployment URL" | awk '{print $3}')

echo "Your webhook URL is: ${DEPLOY_URL}/api/webhook"
echo "Use this URL in your WhatsApp Business API configuration for both accounts."
echo ""
echo "Steps to complete setup:"
echo "1. Go to the Meta Developer Portal (https://developers.facebook.com/)"
echo "2. Set up two WhatsApp Business API accounts"
echo "3. Configure the webhook URL for both accounts: ${DEPLOY_URL}/api/webhook"
echo "4. Add 5 test numbers to each account (10 total)"
echo "5. Test the system by sending messages from the test numbers"
echo ""
echo "Done!" 