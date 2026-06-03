"""
Celery Beat Schedule Configuration for Leave Management System

This file contains the schedule configuration for automated leave management tasks.
Add this to your Django settings.py file or import it in your Celery configuration.

Usage:
1. Install Celery and Redis/RabbitMQ
2. Add this configuration to your settings.py
3. Run Celery worker: celery -A project worker -l info
4. Run Celery beat: celery -A project beat -l info
"""

from celery.schedules import crontab

# Celery Beat Schedule Configuration
CELERY_BEAT_SCHEDULE = {
    # December 31st at midnight - Grant carryforward leaves
    'yearly-carryforward-grant': {
        'task': 'managers.tasks.process_yearly_carryforward_grant',
        'schedule': crontab(minute=0, hour=0, day_of_month=31, month_of_year=12),
        'options': {
            'expires': 3600,  # Task expires after 1 hour if not executed
        }
    },
    
    # March 31st at midnight - Cleanup carryforward leaves
    'yearly-carryforward-cleanup': {
        'task': 'managers.tasks.process_yearly_carryforward_cleanup',
        'schedule': crontab(minute=0, hour=0, day_of_month=31, month_of_year=3),
        'options': {
            'expires': 3600,  # Task expires after 1 hour if not executed
        }
    },
    
    # March 15th at 9 AM - Send reminder about carryforward cleanup
    'carryforward-reminder': {
        'task': 'managers.tasks.send_carryforward_reminder',
        'schedule': crontab(minute=0, hour=9, day_of_month=15, month_of_year=3),
        'options': {
            'expires': 3600,
        }
    },
    
    # Alternative: Using the existing yearly reset task (December 31st)
    'yearly-leave-reset': {
        'task': 'managers.tasks.yearly_leave_reset',
        'schedule': crontab(minute=0, hour=0, day_of_month=31, month_of_year=12),
        'options': {
            'expires': 3600,
        }
    },
    
    # Alternative: Using the existing carryforward cleanup task (March 31st)
    'carryforward-cleanup': {
        'task': 'managers.tasks.carryforward_cleanup',
        'schedule': crontab(minute=0, hour=0, day_of_month=31, month_of_year=3),
        'options': {
            'expires': 3600,
        }
    },
    
    # Daily health check at 2 AM (optional)
    'daily-leave-system-health-check': {
        'task': 'managers.tasks.test_carryforward_system',
        'schedule': crontab(minute=0, hour=2),
        'options': {
            'expires': 1800,  # 30 minutes
        }
    },
}

# Timezone setting
CELERY_TIMEZONE = 'UTC'  # Change to your timezone, e.g., 'Asia/Kolkata'

# Additional Celery configuration
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'  # Change to your Redis URL
CELERY_BROKER_URL = 'redis://localhost:6379/0'      # Change to your broker URL

# Task routing (optional)
CELERY_TASK_ROUTES = {
    'managers.tasks.process_yearly_carryforward_grant': {'queue': 'leave_management'},
    'managers.tasks.process_yearly_carryforward_cleanup': {'queue': 'leave_management'},
    'managers.tasks.yearly_leave_reset': {'queue': 'leave_management'},
    'managers.tasks.carryforward_cleanup': {'queue': 'leave_management'},
}

# Task result expiration
CELERY_RESULT_EXPIRES = 3600  # 1 hour

# Worker configuration
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_ACKS_LATE = True

"""
INSTALLATION INSTRUCTIONS:

1. Install required packages:
   pip install celery redis

2. Add to your Django settings.py:
   from .celery_schedule import *

3. Create celery.py in your project directory:
   
   import os
   from celery import Celery
   
   os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
   
   app = Celery('project')
   app.config_from_object('django.conf:settings', namespace='CELERY')
   app.autodiscover_tasks()

4. Add to your project/__init__.py:
   from .celery import app as celery_app
   __all__ = ('celery_app',)

5. Start Redis server:
   redis-server

6. Start Celery worker:
   celery -A project worker -l info

7. Start Celery beat scheduler:
   celery -A project beat -l info

8. For production, use supervisor or systemd to manage processes.

TESTING:

1. Test the management command directly:
   python manage.py process_carryforward_leaves --action=test --dry-run

2. Test Celery tasks manually:
   python manage.py shell
   >>> from managers.tasks import test_carryforward_system
   >>> test_carryforward_system.delay()

3. Check Celery beat schedule:
   celery -A project beat -l info --dry-run
"""
