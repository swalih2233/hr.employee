from django.core.management.base import BaseCommand
from managers.google_calendar_service import get_google_calendar_service
import os
from django.conf import settings

class Command(BaseCommand):
    help = 'Setup Google Calendar authentication for the first time'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Setting up Google Calendar authentication...'))
        
        # Check if credentials.json exists
        credentials_file = os.path.join(settings.BASE_DIR, 'credentials.json')
        if not os.path.exists(credentials_file):
            self.stdout.write(
                self.style.ERROR(
                    f'credentials.json not found at {credentials_file}. '
                    'Please download it from Google Cloud Console and place it in the project root.'
                )
            )
            return
        
        try:
            # Initialize the service which will trigger authentication
            calendar_service = get_google_calendar_service()
            service = calendar_service.authenticate()
            
            if service:
                self.stdout.write(
                    self.style.SUCCESS(
                        'Google Calendar authentication successful! '
                        'token.json has been created and saved for future use.'
                    )
                )
                
                # Test by listing calendars
                calendars_result = service.calendarList().list().execute()
                calendars = calendars_result.get('items', [])
                
                self.stdout.write(f'Found {len(calendars)} calendar(s):')
                for calendar in calendars:
                    self.stdout.write(f'  - {calendar["summary"]} ({calendar["id"]})')
                    
            else:
                self.stdout.write(self.style.ERROR('Authentication failed.'))
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error during authentication: {e}')
            )
            self.stdout.write(
                self.style.WARNING(
                    'Make sure you have:\n'
                    '1. Downloaded credentials.json from Google Cloud Console\n'
                    '2. Enabled Google Calendar API\n'
                    '3. Set up OAuth 2.0 Client ID\n'
                    '4. Added your domain to authorized domains if needed'
                )
            )
