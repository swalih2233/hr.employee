from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import datetime, date
import logging

from employe.models import Employe
from managers.models import Manager, Founder

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Process carryforward leaves for employees on Dec 31st and cleanup on Mar 31st'

    def add_arguments(self, parser):
        parser.add_argument(
            '--action',
            type=str,
            choices=['grant', 'cleanup', 'test'],
            default='test',
            help='Action to perform: grant (Dec 31), cleanup (Mar 31), or test'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without making actual changes (for testing)'
        )

    def handle(self, *args, **options):
        action = options['action']
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        if action == 'grant':
            self.grant_carryforward_leaves(dry_run)
        elif action == 'cleanup':
            self.cleanup_carryforward_leaves(dry_run)
        elif action == 'test':
            self.test_carryforward_system(dry_run)

    def grant_carryforward_leaves(self, dry_run=False):
        """Grant carryforward leaves on December 31st"""
        self.stdout.write(self.style.SUCCESS('🎄 Processing December 31st carryforward leaves...'))
        
        employees = Employe.objects.all()
        eligible_employees = []
        
        for employee in employees:
            if employee.leaves_taken >= 10:
                eligible_employees.append(employee)
                
                if not dry_run:
                    employee.carryforward_available_leaves = 6
                    employee.carryforward_leaves_taken = 0
                    employee.save()
                
                self.stdout.write(
                    f"✅ {employee.user.first_name} {employee.user.last_name} "
                    f"(Taken: {employee.leaves_taken}) -> 6 carryforward leaves granted"
                )
            else:
                self.stdout.write(
                    f"❌ {employee.user.first_name} {employee.user.last_name} "
                    f"(Taken: {employee.leaves_taken}) -> Not eligible (needs 10+ leaves)"
                )
        
        # Send email notifications
        if eligible_employees and not dry_run:
            self.send_carryforward_notifications(eligible_employees)
        
        self.stdout.write(
            self.style.SUCCESS(
                f'🎉 Carryforward process completed! '
                f'{len(eligible_employees)} employees received carryforward leaves.'
            )
        )

    def cleanup_carryforward_leaves(self, dry_run=False):
        """Cleanup carryforward leaves on March 31st"""
        self.stdout.write(self.style.WARNING('🧹 Processing March 31st carryforward cleanup...'))
        
        employees = Employe.objects.filter(carryforward_available_leaves__gt=0)
        cleanup_count = 0
        
        for employee in employees:
            unused_leaves = employee.carryforward_available_leaves
            
            if not dry_run:
                employee.carryforward_available_leaves = 0
                employee.carryforward_leaves_taken = 0
                employee.save()
            
            cleanup_count += 1
            self.stdout.write(
                f"🗑️  {employee.user.first_name} {employee.user.last_name} "
                f"-> {unused_leaves} unused carryforward leaves removed"
            )
        
        # Send cleanup notifications
        if cleanup_count > 0 and not dry_run:
            self.send_cleanup_notifications(employees)
        
        self.stdout.write(
            self.style.SUCCESS(
                f'🧹 Cleanup completed! {cleanup_count} employees had carryforward leaves reset.'
            )
        )

    def test_carryforward_system(self, dry_run=True):
        """Test the carryforward system with current data"""
        self.stdout.write(self.style.HTTP_INFO('🧪 Testing carryforward system...'))
        
        # Test grant process
        self.stdout.write('\n--- Testing Grant Process (Dec 31st) ---')
        self.grant_carryforward_leaves(dry_run=True)
        
        # Test cleanup process
        self.stdout.write('\n--- Testing Cleanup Process (Mar 31st) ---')
        self.cleanup_carryforward_leaves(dry_run=True)

    def send_carryforward_notifications(self, eligible_employees):
        """Send email notifications to managers and founders about carryforward grants"""
        try:
            # Get all managers and founders
            managers = Manager.objects.all()
            founders = Founder.objects.all()
            
            # Prepare recipient list
            recipients = []
            for manager in managers:
                if manager.user.email:
                    recipients.append(manager.user.email)
            for founder in founders:
                if founder.user.email:
                    recipients.append(founder.user.email)
            
            if not recipients:
                logger.warning("No managers or founders found for carryforward notifications")
                return
            
            # Prepare email content
            subject = "🎄 Year-End Carryforward Leaves Granted - Action Required"
            
            # Create employee summary
            employee_summary = ""
            for emp in eligible_employees:
                employee_summary += f"• {emp.user.first_name} {emp.user.last_name} ({emp.user.email}) - 6 carryforward leaves\n"
            
            plain_message = f"""
Dear Team,

The year-end carryforward leave process has been completed successfully.

SUMMARY:
- Date: {timezone.now().strftime('%Y-%m-%d %H:%M')}
- Eligible Employees: {len(eligible_employees)}
- Carryforward Leaves Granted: 6 leaves per eligible employee
- Validity: Until March 31st, {timezone.now().year + 1}

ELIGIBLE EMPLOYEES:
{employee_summary}

IMPORTANT NOTES:
- These carryforward leaves are valid only until March 31st
- Employees must have taken at least 10 regular leaves to be eligible
- Unused carryforward leaves will be automatically removed on March 31st

Please inform your team members about their carryforward leave allocation.

Best regards,
HR System
"""
            
            # Send email
            send_mail(
                subject,
                plain_message,
                settings.DEFAULT_FROM_EMAIL,
                recipients,
                fail_silently=False
            )
            
            logger.info(f"Carryforward notification sent to {len(recipients)} recipients")
            self.stdout.write(f"📧 Email notifications sent to {len(recipients)} managers/founders")
            
        except Exception as e:
            logger.error(f"Failed to send carryforward notifications: {e}")
            self.stdout.write(self.style.ERROR(f"❌ Failed to send email notifications: {e}"))

    def send_cleanup_notifications(self, affected_employees):
        """Send email notifications about carryforward cleanup"""
        try:
            # Get all managers and founders
            managers = Manager.objects.all()
            founders = Founder.objects.all()
            
            # Prepare recipient list
            recipients = []
            for manager in managers:
                if manager.user.email:
                    recipients.append(manager.user.email)
            for founder in founders:
                if founder.user.email:
                    recipients.append(founder.user.email)
            
            if not recipients:
                return
            
            # Prepare email content
            subject = "🧹 Carryforward Leaves Cleanup Completed"
            
            plain_message = f"""
Dear Team,

The March 31st carryforward leave cleanup has been completed.

SUMMARY:
- Date: {timezone.now().strftime('%Y-%m-%d %H:%M')}
- Affected Employees: {len(affected_employees)}
- Action: All unused carryforward leaves have been reset to 0

All carryforward leaves from the previous year have been automatically removed as per policy.
The new leave year has begun with fresh allocations.

Best regards,
HR System
"""
            
            # Send email
            send_mail(
                subject,
                plain_message,
                settings.DEFAULT_FROM_EMAIL,
                recipients,
                fail_silently=False
            )
            
            logger.info(f"Cleanup notification sent to {len(recipients)} recipients")
            self.stdout.write(f"📧 Cleanup notifications sent to {len(recipients)} managers/founders")
            
        except Exception as e:
            logger.error(f"Failed to send cleanup notifications: {e}")
            self.stdout.write(self.style.ERROR(f"❌ Failed to send cleanup notifications: {e}"))
