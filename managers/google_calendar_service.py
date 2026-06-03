import os
import json
from datetime import datetime, timedelta
from django.conf import settings
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import logging

logger = logging.getLogger(__name__)

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar']

class GoogleCalendarService:
    def __init__(self):
        self.service = None
        self.credentials_file = os.path.join(settings.BASE_DIR, 'credentials.json')
        self.token_file = os.path.join(settings.BASE_DIR, 'token.json')
        
    def authenticate(self):
        """Authenticate and return Google Calendar service."""
        creds = None
        
        # The file token.json stores the user's access and refresh tokens.
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
        
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    logger.error(f"Error refreshing credentials: {e}")
                    # If refresh fails, we need to re-authenticate
                    creds = None
            
            if not creds:
                if not os.path.exists(self.credentials_file):
                    raise FileNotFoundError(f"Credentials file not found: {self.credentials_file}")
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save the credentials for the next run
            with open(self.token_file, 'w') as token:
                token.write(creds.to_json())
        
        self.service = build('calendar', 'v3', credentials=creds)
        return self.service
    
    def create_leave_event(self, employee_name, employee_email, leave_subject, start_date, end_date, leave_type):
        """Create a calendar event for the leave request."""
        if not self.service:
            self.authenticate()
        
        # Convert dates to datetime objects if they're not already
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        # Create event details
        event_summary = f"{employee_name} - {leave_subject}"
        event_description = f"""
Employee: {employee_name} ({employee_email})
Leave Type: {leave_type}
Subject: {leave_subject}
Duration: {start_date} to {end_date}

This leave has been approved and added to the calendar automatically.
        """.strip()
        
        # For all-day events, we use date format
        event = {
            'summary': event_summary,
            'description': event_description,
            'start': {
                'date': start_date.strftime('%Y-%m-%d'),
                'timeZone': 'UTC',
            },
            'end': {
                'date': (end_date + timedelta(days=1)).strftime('%Y-%m-%d'),  # End date is exclusive for all-day events
                'timeZone': 'UTC',
            },
            'attendees': [
                {'email': employee_email},
            ],
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60},  # 1 day before
                    {'method': 'popup', 'minutes': 60},       # 1 hour before
                ],
            },
        }
        
        return event
    
    def add_event_to_calendar(self, calendar_email, event):
        """Add an event to a specific calendar."""
        if not self.service:
            self.authenticate()
        
        try:
            # First, try to find the calendar by email
            calendar_id = self.get_calendar_id_by_email(calendar_email)
            if not calendar_id:
                logger.warning(f"Calendar not found for email: {calendar_email}")
                return None
            
            created_event = self.service.events().insert(
                calendarId=calendar_id,
                body=event
            ).execute()
            
            logger.info(f"Event created successfully in {calendar_email}'s calendar: {created_event.get('htmlLink')}")
            return created_event
            
        except HttpError as error:
            logger.error(f"An error occurred while adding event to {calendar_email}: {error}")
            return None
    
    def get_calendar_id_by_email(self, email):
        """Get calendar ID by email address."""
        if not self.service:
            self.authenticate()
        
        try:
            # For primary calendar, use 'primary' or the email address
            if email:
                return email  # Gmail addresses can be used directly as calendar IDs
            return 'primary'
            
        except HttpError as error:
            logger.error(f"Error getting calendar ID for {email}: {error}")
            return None
    
    def add_leave_to_calendars(self, employee_name, employee_email, leave_subject, start_date, end_date, leave_type, manager_email, founder_emails):
        """Add leave event to manager's and all founders' calendars."""
        if not self.service:
            self.authenticate()
        
        # Create the event
        event = self.create_leave_event(
            employee_name, employee_email, leave_subject, 
            start_date, end_date, leave_type
        )
        
        results = []
        
        # Add to manager's calendar
        if manager_email:
            manager_result = self.add_event_to_calendar(manager_email, event)
            results.append({
                'email': manager_email,
                'type': 'manager',
                'success': manager_result is not None,
                'event': manager_result
            })
        
        # Add to all founders' calendars
        for founder_email in founder_emails:
            if founder_email:
                founder_result = self.add_event_to_calendar(founder_email, event)
                results.append({
                    'email': founder_email,
                    'type': 'founder',
                    'success': founder_result is not None,
                    'event': founder_result
                })
        
        return results

def get_google_calendar_service():
    """Factory function to get Google Calendar service instance."""
    return GoogleCalendarService()
