"""
APScheduler-based Leave Management Scheduler

Alternative to Celery for automated leave management tasks.
This uses APScheduler which is simpler to set up and doesn't require Redis/RabbitMQ.

Usage:
1. Install APScheduler: pip install apscheduler
2. Add this to your Django app startup (apps.py or management command)
3. Run your Django server normally
"""

import logging
from datetime import datetime, date
from django.core.management import call_command
from django.conf import settings

# Only import if APScheduler is available
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.executors.pool import ThreadPoolExecutor
    APSCHEDULER_AVAILABLE = True
except ImportError:
    APSCHEDULER_AVAILABLE = False

logger = logging.getLogger(__name__)


class LeaveManagementScheduler:
    """
    APScheduler-based scheduler for leave management tasks
    """
    
    def __init__(self):
        if not APSCHEDULER_AVAILABLE:
            raise ImportError("APScheduler is not installed. Run: pip install apscheduler")
        
        # Configure scheduler
        executors = {
            'default': ThreadPoolExecutor(20),
        }
        
        job_defaults = {
            'coalesce': False,
            'max_instances': 1,
            'misfire_grace_time': 3600  # 1 hour grace time
        }
        
        self.scheduler = BackgroundScheduler(
            executors=executors,
            job_defaults=job_defaults,
            timezone='UTC'  # Change to your timezone
        )
        
        self._setup_jobs()
    
    def _setup_jobs(self):
        """Setup all scheduled jobs"""
        
        # December 31st at midnight - Grant carryforward leaves
        self.scheduler.add_job(
            func=self.grant_carryforward_leaves,
            trigger=CronTrigger(month=12, day=31, hour=0, minute=0),
            id='yearly_carryforward_grant',
            name='Yearly Carryforward Grant',
            replace_existing=True
        )
        
        # March 31st at midnight - Cleanup carryforward leaves
        self.scheduler.add_job(
            func=self.cleanup_carryforward_leaves,
            trigger=CronTrigger(month=3, day=31, hour=0, minute=0),
            id='yearly_carryforward_cleanup',
            name='Yearly Carryforward Cleanup',
            replace_existing=True
        )
        
        # March 15th at 9 AM - Send reminder
        self.scheduler.add_job(
            func=self.send_carryforward_reminder,
            trigger=CronTrigger(month=3, day=15, hour=9, minute=0),
            id='carryforward_reminder',
            name='Carryforward Reminder',
            replace_existing=True
        )
        
        # Optional: Daily health check at 2 AM
        self.scheduler.add_job(
            func=self.daily_health_check,
            trigger=CronTrigger(hour=2, minute=0),
            id='daily_health_check',
            name='Daily Health Check',
            replace_existing=True
        )
    
    def grant_carryforward_leaves(self):
        """Grant carryforward leaves on December 31st"""
        try:
            logger.info("Starting scheduled carryforward grant process...")
            call_command('process_carryforward_leaves', action='grant')
            logger.info("Scheduled carryforward grant completed successfully")
        except Exception as e:
            logger.error(f"Scheduled carryforward grant failed: {e}")
    
    def cleanup_carryforward_leaves(self):
        """Cleanup carryforward leaves on March 31st"""
        try:
            logger.info("Starting scheduled carryforward cleanup process...")
            call_command('process_carryforward_leaves', action='cleanup')
            logger.info("Scheduled carryforward cleanup completed successfully")
        except Exception as e:
            logger.error(f"Scheduled carryforward cleanup failed: {e}")
    
    def send_carryforward_reminder(self):
        """Send carryforward reminder on March 15th"""
        try:
            logger.info("Sending scheduled carryforward reminder...")
            # You can implement a specific reminder command or use existing tasks
            from managers.tasks import send_carryforward_reminder
            send_carryforward_reminder()
            logger.info("Scheduled carryforward reminder sent successfully")
        except Exception as e:
            logger.error(f"Scheduled carryforward reminder failed: {e}")
    
    def daily_health_check(self):
        """Daily health check (optional)"""
        try:
            logger.info("Running daily leave system health check...")
            call_command('process_carryforward_leaves', action='test', dry_run=True)
            logger.info("Daily health check completed successfully")
        except Exception as e:
            logger.error(f"Daily health check failed: {e}")
    
    def start(self):
        """Start the scheduler"""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Leave management scheduler started successfully")
            
            # Log scheduled jobs
            jobs = self.scheduler.get_jobs()
            for job in jobs:
                logger.info(f"Scheduled job: {job.name} - Next run: {job.next_run_time}")
    
    def stop(self):
        """Stop the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Leave management scheduler stopped")
    
    def get_jobs(self):
        """Get list of scheduled jobs"""
        return self.scheduler.get_jobs()
    
    def run_job_now(self, job_id):
        """Manually trigger a specific job"""
        try:
            job = self.scheduler.get_job(job_id)
            if job:
                job.func()
                logger.info(f"Manually triggered job: {job_id}")
                return True
            else:
                logger.error(f"Job not found: {job_id}")
                return False
        except Exception as e:
            logger.error(f"Failed to run job {job_id}: {e}")
            return False


# Global scheduler instance
_scheduler = None


def get_scheduler():
    """Get the global scheduler instance"""
    global _scheduler
    if _scheduler is None:
        _scheduler = LeaveManagementScheduler()
    return _scheduler


def start_scheduler():
    """Start the leave management scheduler"""
    scheduler = get_scheduler()
    scheduler.start()
    return scheduler


def stop_scheduler():
    """Stop the leave management scheduler"""
    global _scheduler
    if _scheduler:
        _scheduler.stop()
        _scheduler = None


# Management functions for manual testing
def trigger_carryforward_grant():
    """Manually trigger carryforward grant"""
    scheduler = get_scheduler()
    return scheduler.run_job_now('yearly_carryforward_grant')


def trigger_carryforward_cleanup():
    """Manually trigger carryforward cleanup"""
    scheduler = get_scheduler()
    return scheduler.run_job_now('yearly_carryforward_cleanup')


def trigger_carryforward_reminder():
    """Manually trigger carryforward reminder"""
    scheduler = get_scheduler()
    return scheduler.run_job_now('carryforward_reminder')


def list_scheduled_jobs():
    """List all scheduled jobs"""
    scheduler = get_scheduler()
    jobs = scheduler.get_jobs()
    
    job_info = []
    for job in jobs:
        job_info.append({
            'id': job.id,
            'name': job.name,
            'next_run': job.next_run_time,
            'trigger': str(job.trigger)
        })
    
    return job_info


"""
USAGE INSTRUCTIONS:

1. Install APScheduler:
   pip install apscheduler

2. Add to your Django app's apps.py:

   from django.apps import AppConfig
   
   class ManagersConfig(AppConfig):
       default_auto_field = 'django.db.models.BigAutoField'
       name = 'managers'
       
       def ready(self):
           # Start the scheduler when Django starts
           from .scheduler import start_scheduler
           start_scheduler()

3. Or create a management command to start the scheduler:

   # managers/management/commands/start_scheduler.py
   from django.core.management.base import BaseCommand
   from managers.scheduler import start_scheduler
   
   class Command(BaseCommand):
       help = 'Start the leave management scheduler'
       
       def handle(self, *args, **options):
           scheduler = start_scheduler()
           self.stdout.write('Scheduler started successfully')
           
           # Keep the command running
           try:
               import time
               while True:
                   time.sleep(1)
           except KeyboardInterrupt:
               scheduler.stop()
               self.stdout.write('Scheduler stopped')

4. Test manually:
   python manage.py shell
   >>> from managers.scheduler import trigger_carryforward_grant
   >>> trigger_carryforward_grant()

5. List scheduled jobs:
   >>> from managers.scheduler import list_scheduled_jobs
   >>> jobs = list_scheduled_jobs()
   >>> for job in jobs:
   ...     print(f"{job['name']}: {job['next_run']}")
"""
