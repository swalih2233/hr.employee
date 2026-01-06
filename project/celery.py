"""
Celery configuration for automated leave management system
"""
import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')

app = Celery('leave_management')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Celery Beat schedule for automated leave management
app.conf.beat_schedule = {
    # Yearly leave reset on December 31st at 11:59 PM
    'yearly-leave-reset': {
        'task': 'managers.tasks.yearly_leave_reset',
        'schedule': {
            'minute': 59,
            'hour': 23,
            'day_of_month': 31,
            'month_of_year': 12,
        },
    },
    
    # Carryforward cleanup on March 31st at 11:59 PM
    'carryforward-cleanup': {
        'task': 'managers.tasks.carryforward_cleanup',
        'schedule': {
            'minute': 59,
            'hour': 23,
            'day_of_month': 31,
            'month_of_year': 3,
        },
    },
    
    # Notification reminder on March 15th at 9:00 AM
    'carryforward-reminder': {
        'task': 'managers.tasks.send_carryforward_reminder',
        'schedule': {
            'minute': 0,
            'hour': 9,
            'day_of_month': 15,
            'month_of_year': 3,
        },
    },

    # Daily health check at 2 AM
    'daily-leave-system-health-check': {
        'task': 'managers.tasks.test_carryforward_system',
        'schedule': {
            'minute': 0,
            'hour': 2,
        },
    },
}

# Timezone configuration
app.conf.timezone = 'UTC'

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')


# Celery configuration
app.conf.update(
    # Task serialization
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    
    # Task routing
    task_routes={
        'managers.tasks.*': {'queue': 'leave_management'},
    },
    
    # Task execution
    task_always_eager=False,
    task_eager_propagates=True,
    
    # Results backend
    result_expires=3600,
    
    # Worker configuration
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)
