"""
Management command to setup Celery Beat periodic tasks for leave management
"""
from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask, CrontabSchedule
import json


class Command(BaseCommand):
    help = 'Setup Celery Beat periodic tasks for automated leave management'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Reset existing tasks before creating new ones',
        )

    def handle(self, *args, **options):
        if options['reset']:
            self.stdout.write('Resetting existing periodic tasks...')
            PeriodicTask.objects.filter(
                name__in=[
                    'Yearly Leave Reset',
                    'Carryforward Cleanup',
                    'Carryforward Reminder'
                ]
            ).delete()

        # Create crontab schedules
        
        # December 31st at 11:59 PM
        yearly_reset_schedule, created = CrontabSchedule.objects.get_or_create(
            minute=59,
            hour=23,
            day_of_month=31,
            month_of_year=12,
            day_of_week='*',
            timezone='UTC'
        )
        if created:
            self.stdout.write(f'Created yearly reset schedule: {yearly_reset_schedule}')

        # March 31st at 11:59 PM
        carryforward_cleanup_schedule, created = CrontabSchedule.objects.get_or_create(
            minute=59,
            hour=23,
            day_of_month=31,
            month_of_year=3,
            day_of_week='*',
            timezone='UTC'
        )
        if created:
            self.stdout.write(f'Created carryforward cleanup schedule: {carryforward_cleanup_schedule}')

        # March 15th at 9:00 AM
        carryforward_reminder_schedule, created = CrontabSchedule.objects.get_or_create(
            minute=0,
            hour=9,
            day_of_month=15,
            month_of_year=3,
            day_of_week='*',
            timezone='UTC'
        )
        if created:
            self.stdout.write(f'Created carryforward reminder schedule: {carryforward_reminder_schedule}')

        # Create periodic tasks
        
        # Yearly Leave Reset Task
        yearly_reset_task, created = PeriodicTask.objects.get_or_create(
            name='Yearly Leave Reset',
            defaults={
                'crontab': yearly_reset_schedule,
                'task': 'managers.tasks.yearly_leave_reset',
                'enabled': True,
                'description': 'Automated yearly leave reset on December 31st'
            }
        )
        if created:
            self.stdout.write(
                self.style.SUCCESS(f'✅ Created yearly reset task: {yearly_reset_task.name}')
            )
        else:
            self.stdout.write(f'Yearly reset task already exists: {yearly_reset_task.name}')

        # Carryforward Cleanup Task
        carryforward_cleanup_task, created = PeriodicTask.objects.get_or_create(
            name='Carryforward Cleanup',
            defaults={
                'crontab': carryforward_cleanup_schedule,
                'task': 'managers.tasks.carryforward_cleanup',
                'enabled': True,
                'description': 'Automated carryforward cleanup on March 31st'
            }
        )
        if created:
            self.stdout.write(
                self.style.SUCCESS(f'✅ Created carryforward cleanup task: {carryforward_cleanup_task.name}')
            )
        else:
            self.stdout.write(f'Carryforward cleanup task already exists: {carryforward_cleanup_task.name}')

        # Carryforward Reminder Task
        carryforward_reminder_task, created = PeriodicTask.objects.get_or_create(
            name='Carryforward Reminder',
            defaults={
                'crontab': carryforward_reminder_schedule,
                'task': 'managers.tasks.send_carryforward_reminder',
                'enabled': True,
                'description': 'Send carryforward reminder on March 15th'
            }
        )
        if created:
            self.stdout.write(
                self.style.SUCCESS(f'✅ Created carryforward reminder task: {carryforward_reminder_task.name}')
            )
        else:
            self.stdout.write(f'Carryforward reminder task already exists: {carryforward_reminder_task.name}')

        self.stdout.write(
            self.style.SUCCESS('\n🎉 Celery Beat setup completed successfully!')
        )
        self.stdout.write('\nCreated tasks:')
        self.stdout.write(f'  • {yearly_reset_task.name} - {yearly_reset_schedule}')
        self.stdout.write(f'  • {carryforward_cleanup_task.name} - {carryforward_cleanup_schedule}')
        self.stdout.write(f'  • {carryforward_reminder_task.name} - {carryforward_reminder_schedule}')
        
        self.stdout.write('\nTo start Celery Beat, run:')
        self.stdout.write('  celery -A project beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler')
        
        self.stdout.write('\nTo start Celery Worker, run:')
        self.stdout.write('  celery -A project worker -l info')
