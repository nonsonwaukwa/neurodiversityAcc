# Neurodiversity Accountability App: Reminder System Guide

This guide explains how to properly set up and troubleshoot the reminder system, which is crucial for supporting neurodivergent users by providing timely follow-ups.

## Why Reminders Are Critical for Neurodivergent Users

For neurodivergent individuals, reminders serve several vital functions:

1. **Executive Function Support**: Many neurodivergent people face challenges with executive function, making it difficult to initiate tasks or sustain attention. Reminders provide external scaffolding for these executive functions.

2. **Reduced Cognitive Load**: Regular gentle check-ins help reduce the cognitive load that comes with task management, allowing neurodivergent users to focus their energy on meaningful activities.

3. **Consistency and Predictability**: Predictable reminders create a sense of structure and routine, which is often essential for neurodivergent individuals.

4. **Emotional Support**: Well-timed reminders communicate care and support, reducing the isolation that many neurodivergent people experience.

5. **Reduced Anxiety**: Without follow-ups, neurodivergent users may experience heightened anxiety about missing tasks or obligations.

## System Components

The reminder system consists of three main components:

1. **Check-in Database**: Firebase Firestore stores all user check-ins and responses.
2. **WhatsApp Integration**: The application uses WhatsApp to deliver reminders.
3. **Cron Jobs**: Scheduled tasks that trigger reminders at appropriate intervals.

## Quick Fix for Missing Reminders

If users are not receiving reminders, follow these immediate steps:

1. **Update Environment Variables**:
   Edit your `.env` file to include these settings:
   ```
   # WhatsApp API Settings 
   WHATSAPP_API_URL=https://graph.facebook.com/v17.0
   WHATSAPP_PHONE_ID_0=YOUR_PHONE_ID_HERE
   WHATSAPP_ACCESS_TOKEN_0=YOUR_ACCESS_TOKEN_HERE
   
   # Cron Job Settings
   ENABLE_CRON=True
   CRON_SECRET=YOUR_SECRET_HERE
   ```

2. **Create Missing Firestore Index**:
   Open this URL to create the required index:
   ```
   https://console.firebase.google.com/v1/r/project/neurodiversityacc/firestore/indexes?create_composite=ClJwcm9qZWN0cy9uZXVyb2RpdmVyc2l0eWFjYy9kYXRhYmFzZXMvKGRlZmF1bHQpL2NvbGxlY3Rpb25Hcm91cHMvY2hlY2tpbnMvaW5kZXhlcy9fEAEaDwoLaXNfcmVzcG9uc2UQARoLCgd1c2VyX2lkEAEaDgoKY3JlYXRlZF9hdBACGgwKCF9fbmFtZV9fEAI
   ```

3. **Manually Send Reminders**:
   Run the direct reminder tool to create follow-up messages:
   ```
   python send_direct_reminder.py
   ```

## Complete Setup Guide

### 1. Firestore Indexes

Create the following composite indexes in Firebase Console:

| Collection | Fields to index | Query scope |
|------------|----------------|-------------|
| checkins   | user_id Ascending, is_response Ascending, created_at Descending | Collection |
| checkins   | user_id Ascending, created_at Descending | Collection |
| checkins   | is_response Ascending, user_id Ascending, created_at Descending | Collection |

### 2. WhatsApp API Configuration

1. Create a WhatsApp Business account
2. Get your Phone ID and access token 
3. Add to .env:
   ```
   WHATSAPP_API_URL=https://graph.facebook.com/v17.0
   WHATSAPP_PHONE_ID_0=YOUR_PHONE_ID_HERE
   WHATSAPP_ACCESS_TOKEN_0=YOUR_ACCESS_TOKEN_HERE
   ```

### 3. Cron Job Configuration

1. Enable cron in .env:
   ```
   ENABLE_CRON=True
   CRON_SECRET=YOUR_SECRET_HERE
   ```

2. Set up the cron schedules:
   ```
   # Cron Schedules (UTC timezone)
   DAILY_CHECKIN_CRON=0 8 * * *  # 8:00 AM UTC daily
   DAILY_TASKS_CRON=0 9 * * *    # 9:00 AM UTC daily
   WEEKLY_CHECKIN_CRON=0 9 * * 0 # 9:00 AM UTC Sunday
   WEEKLY_REPORT_CRON=0 10 * * 6 # 10:00 AM UTC Saturday
   
   # Followup Reminder Crons
   MORNING_FOLLOWUP_CRON=0 12 * * * # Noon UTC
   MIDDAY_FOLLOWUP_CRON=0 14 * * *  # 2:00 PM UTC
   EVENING_FOLLOWUP_CRON=0 18 * * *  # 6:00 PM UTC
   ```

3. On Railway, create cron job services for each reminder type

## Reminder Windows

Reminders are sent at these intervals after the last check-in:

- **Morning Reminder**: 1.5-2.5 hours after check-in
- **Mid-day Check**: 3.5-4.5 hours after check-in
- **Evening Reset**: 7.5-8.5 hours after check-in
- **Next Day Support**: >24 hours after check-in

## Troubleshooting

### Diagnostic Tools

1. **Check Reminder Eligibility**:
   ```
   python check_simplified.py
   ```

2. **Create Manual Reminder**:
   ```
   python send_direct_reminder.py
   ```

3. **Verify Cron Settings**:
   ```
   python fix_reminder_system.py
   ```

### Common Issues

1. **Missing WhatsApp credentials**: Update .env with valid WhatsApp API credentials
2. **Cron jobs not running**: Set ENABLE_CRON=True and verify cron job services on Railway
3. **Missing Firestore indexes**: Create required indexes in Firebase console
4. **Timezone issues**: Ensure all datetime operations use timezone-aware datetimes

## Additional Support

For further assistance, check the project repository or contact the development team. Remember that consistent, well-functioning reminders are a crucial accessibility feature for neurodivergent users. 