# Google Calendar Integration Setup

This document explains how to set up and use the Google Calendar integration for the leave management system.

## Overview

When a manager approves a leave request, the system automatically:
1. Creates a calendar event with leave details
2. Adds the event to the manager's Google Calendar
3. Adds the event to all founders' Google Calendars

## Prerequisites

✅ You already have:
- Google Cloud Project created
- Google Calendar API enabled
- OAuth 2.0 Client ID created
- `credentials.json` downloaded

## Setup Instructions

### 1. Install Required Dependencies

The required packages are already in your `r.txt` file:
```bash
pip install google-auth google-auth-oauthlib google-api-python-client
```

Or install from your requirements file:
```bash
pip install -r r.txt
```

### 2. Configure OAuth Consent Screen

Before authentication, you need to configure the OAuth consent screen:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to **APIs & Services** → **OAuth consent screen**
3. Choose one of these options:

   **Option A: Add Test Users (Recommended)**
   - Scroll to **Test users** section
   - Click **ADD USERS**
   - Add all email addresses that need calendar access:
     - Manager emails
     - Founder emails
     - Any other users

   **Option B: Use Internal User Type (If applicable)**
   - Change **User Type** from "External" to "Internal"
   - This works if all users are in the same Google Workspace

### 3. Initial Authentication

After configuring the consent screen, run the setup command:
```bash
python manage.py setup_google_calendar
```

This will:
- Open a browser window for Google OAuth
- Ask you to sign in with a Google account that has access to the calendars
- Create a `token.json` file for future authentication

**Important**:
- Use a Google account that has access to all the calendars you want to add events to
- The account must be added as a test user (if using External user type)
- If you see "Access blocked" error, add the email to test users in OAuth consent screen

### 3. Test the Integration

Run the test script to verify everything works:
```bash
python test_calendar_integration.py
```

## How It Works

### In the `approve_leave` View

When a manager approves a leave request, the system:

1. **Gets Calendar Recipients**:
   - Manager's email: Current user who approved the leave
   - Founders' emails: All users in the `Founder` model

2. **Creates Calendar Event**:
   - Summary: "Employee Name - Leave Subject"
   - Description: Includes employee details, leave type, and dates
   - All-day event spanning the leave period
   - Includes the employee as an attendee

3. **Adds to Multiple Calendars**:
   - Manager's calendar
   - All founders' calendars

### Event Details

The calendar event includes:
- **Title**: `{Employee Name} - {Leave Subject}`
- **Description**: Employee details, leave type, dates
- **Duration**: All-day event from start date to end date
- **Attendees**: The employee on leave
- **Reminders**: Email reminder 1 day before, popup 1 hour before

## File Structure

```
managers/
├── google_calendar_service.py      # Main calendar service
├── management/
│   └── commands/
│       └── setup_google_calendar.py  # Setup command
└── views.py                        # Updated approve_leave view

credentials.json                    # Google OAuth credentials (you provided)
token.json                         # Generated after first auth (auto-created)
test_calendar_integration.py       # Test script
```

## Configuration

### Calendar Access

The system uses the email addresses from your Django models:
- **Manager**: `request.user.email` (current user approving the leave)
- **Founders**: `founder.user.email` for all `Founder` objects

### Permissions Required

The Google account used for authentication needs:
- Access to Google Calendar API
- Permission to create events in the target calendars
- If using shared calendars, appropriate sharing permissions

## Troubleshooting

### Common Issues

1. **"Access blocked: App not verified" error**:
   - Go to Google Cloud Console → APIs & Services → OAuth consent screen
   - Add the email address to **Test users** section
   - Or change User Type to "Internal" if using Google Workspace

2. **"Calendar not found" errors**:
   - Ensure the email addresses in your database are correct
   - Verify the authenticated Google account has access to those calendars

3. **Authentication errors**:
   - Delete `token.json` and run `python manage.py setup_google_calendar` again
   - Check that `credentials.json` is in the project root
   - Verify the email is added as a test user in OAuth consent screen

4. **Permission errors**:
   - Ensure the Google account has calendar access
   - Check Google Cloud Console for API quotas and limits
   - Verify Calendar API is enabled

### Logging

The system logs calendar integration results:
- Successful calendar additions
- Failed calendar additions with reasons
- Authentication issues

Check Django logs for detailed error information.

## Security Notes

### File Security

- `credentials.json`: Contains OAuth client secrets - keep secure
- `token.json`: Contains access tokens - keep secure and don't commit to version control

### Add to .gitignore

```gitignore
token.json
credentials.json  # If you want to keep it out of version control
```

## Testing

### Manual Testing

1. Create a test leave request
2. Approve it as a manager
3. Check the manager's and founders' Google Calendars
4. Verify the event appears with correct details

### Automated Testing

Use the provided test script:
```bash
python test_calendar_integration.py
```

## Customization

### Modifying Event Details

Edit the `create_leave_event` method in `google_calendar_service.py` to customize:
- Event title format
- Description content
- Reminder settings
- Event duration (currently all-day events)

### Adding More Recipients

Modify the `approve_leave` view to include additional calendar recipients:
```python
# Add HR team calendars
hr_emails = ["hr1@company.com", "hr2@company.com"]
founder_emails.extend(hr_emails)
```

## Support

If you encounter issues:
1. Check the Django logs for error details
2. Verify Google Cloud Console settings
3. Test with the provided test script
4. Ensure all email addresses are valid and accessible
