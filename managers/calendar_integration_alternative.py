"""
Alternative calendar integration approach for testing/development.
This creates calendar events in a simpler format that can be imported manually.
"""

import os
import json
from datetime import datetime, timedelta
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class AlternativeCalendarService:
    """
    Alternative calendar service that creates calendar files
    instead of directly integrating with Google Calendar API.
    """
    
    def __init__(self):
        self.events_dir = os.path.join(settings.BASE_DIR, 'calendar_events')
        if not os.path.exists(self.events_dir):
            os.makedirs(self.events_dir)
    
    def create_ics_event(self, employee_name, employee_email, leave_subject, start_date, end_date, leave_type):
        """Create an ICS (iCalendar) file that can be imported into any calendar."""
        
        # Convert dates to datetime objects if they're not already
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        # Create ICS content
        event_uid = f"leave-{employee_email}-{start_date}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        ics_content = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Leave Management System//EN
BEGIN:VEVENT
UID:{event_uid}
DTSTART;VALUE=DATE:{start_date.strftime('%Y%m%d')}
DTEND;VALUE=DATE:{(end_date + timedelta(days=1)).strftime('%Y%m%d')}
SUMMARY:{employee_name} - {leave_subject}
DESCRIPTION:Employee: {employee_name} ({employee_email})\\nLeave Type: {leave_type}\\nSubject: {leave_subject}\\nDuration: {start_date} to {end_date}\\n\\nThis leave has been approved and added to the calendar automatically.
ATTENDEE:MAILTO:{employee_email}
STATUS:CONFIRMED
TRANSP:TRANSPARENT
END:VEVENT
END:VCALENDAR"""
        
        return ics_content, event_uid
    
    def save_calendar_event(self, employee_name, employee_email, leave_subject, start_date, end_date, leave_type, recipients):
        """Save calendar event as ICS file and create summary."""
        
        ics_content, event_uid = self.create_ics_event(
            employee_name, employee_email, leave_subject, start_date, end_date, leave_type
        )
        
        # Save ICS file
        filename = f"leave_event_{event_uid}.ics"
        filepath = os.path.join(self.events_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(ics_content)
        
        # Create summary file
        summary = {
            'event_id': event_uid,
            'employee_name': employee_name,
            'employee_email': employee_email,
            'leave_subject': leave_subject,
            'start_date': str(start_date),
            'end_date': str(end_date),
            'leave_type': leave_type,
            'recipients': recipients,
            'ics_file': filename,
            'created_at': datetime.now().isoformat(),
            'instructions': [
                f"1. Download the file: {filename}",
                "2. Open your Google Calendar",
                "3. Click the '+' button next to 'Other calendars'",
                "4. Select 'Import'",
                "5. Choose the downloaded .ics file",
                "6. Select the calendar to import to",
                "7. Click 'Import'"
            ]
        }
        
        summary_filename = f"leave_event_{event_uid}_summary.json"
        summary_filepath = os.path.join(self.events_dir, summary_filename)
        
        with open(summary_filepath, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"Calendar event saved: {filepath}")
        logger.info(f"Summary saved: {summary_filepath}")
        
        return {
            'success': True,
            'ics_file': filepath,
            'summary_file': summary_filepath,
            'event_id': event_uid,
            'recipients': recipients
        }
    
    def add_leave_to_calendars_alternative(self, employee_name, employee_email, leave_subject, start_date, end_date, leave_type, manager_email, founder_emails):
        """Alternative method that creates importable calendar files."""
        
        recipients = []
        if manager_email:
            recipients.append({'email': manager_email, 'type': 'manager'})
        
        for founder_email in founder_emails:
            if founder_email:
                recipients.append({'email': founder_email, 'type': 'founder'})
        
        result = self.save_calendar_event(
            employee_name, employee_email, leave_subject, 
            start_date, end_date, leave_type, recipients
        )
        
        return [result]

def get_alternative_calendar_service():
    """Factory function to get alternative calendar service instance."""
    return AlternativeCalendarService()
