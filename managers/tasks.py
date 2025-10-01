"""
Celery tasks for automated leave management system
"""
import logging
from datetime import datetime, date
from django.conf import settings
from django.core.mail import send_mail
from django.core.management import call_command
from django.template.loader import render_to_string
from django.utils.html import strip_tags
# Temporarily disabled until Celery is installed
# from celery import shared_task

# Dummy decorator for when Celery is not available
def shared_task(*args, **kwargs):
    def decorator(func):
        return func
    return decorator
from django.db import transaction

from .models import Manager, Founder
from employe.models import Employe

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def yearly_leave_reset(self):
    """
    Automated yearly leave reset task - runs on December 31st
    
    Rules:
    - If available_leaves >= 10, carry forward 6 leaves
    - Reset available_leaves = 18
    - Reset leaves_taken = 0
    - Reset available_medical_leaves = 14
    """
    try:
        with transaction.atomic():
            # Get configuration
            config = settings.LEAVE_MANAGEMENT_CONFIG
            annual_allocation = config['ANNUAL_LEAVE_ALLOCATION']
            medical_allocation = config['MEDICAL_LEAVE_ALLOCATION']
            carryforward_limit = config['CARRYFORWARD_LIMIT']
            eligibility_threshold = config['CARRYFORWARD_ELIGIBILITY_THRESHOLD']
            
            # Process all employees
            employees = Employe.objects.all()
            managers = Manager.objects.all()
            
            stats = {
                'total_employees': 0,
                'total_managers': 0,
                'employees_with_carryforward': 0,
                'managers_with_carryforward': 0,
                'total_carryforward_leaves': 0,
            }
            
            # Process employees
            for employee in employees:
                stats['total_employees'] += 1
                
                # Check carryforward eligibility
                if employee.available_leaves >= eligibility_threshold:
                    employee.carryforward_available_leaves = carryforward_limit
                    stats['employees_with_carryforward'] += 1
                    stats['total_carryforward_leaves'] += carryforward_limit
                else:
                    employee.carryforward_available_leaves = 0
                
                # Reset yearly allocations
                employee.available_leaves = annual_allocation
                employee.leaves_taken = 0
                employee.available_medical_leaves = medical_allocation
                employee.medical_leaves_taken = 0
                employee.carryforward_leaves_taken = 0
                
                employee.save()
            
            # Process managers
            for manager in managers:
                stats['total_managers'] += 1
                
                # Check carryforward eligibility
                if manager.available_leaves >= eligibility_threshold:
                    manager.carryforward_available_leaves = carryforward_limit
                    stats['managers_with_carryforward'] += 1
                    stats['total_carryforward_leaves'] += carryforward_limit
                else:
                    manager.carryforward_available_leaves = 0
                
                # Reset yearly allocations
                manager.available_leaves = annual_allocation
                manager.leaves_taken = 0
                manager.available_medical_leaves = medical_allocation
                manager.medical_leaves_taken = 0
                manager.carryforward_leaves_taken = 0
                
                manager.save()
            
            # Send notification emails
            send_yearly_reset_notification.delay(stats)
            
            logger.info(f"Yearly leave reset completed successfully. Stats: {stats}")
            return {
                'status': 'success',
                'message': 'Yearly leave reset completed successfully',
                'stats': stats
            }
            
    except Exception as exc:
        logger.error(f"Yearly leave reset failed: {exc}")
        # Retry the task
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def carryforward_cleanup(self):
    """
    Carryforward cleanup task - runs on March 31st
    
    Rules:
    - Set carryforward_available_leaves = 0
    - Set carryforward_leaves_taken = 0
    - If available_leaves > 18, reset to 18
    """
    try:
        with transaction.atomic():
            config = settings.LEAVE_MANAGEMENT_CONFIG
            annual_allocation = config['ANNUAL_LEAVE_ALLOCATION']
            
            # Process all employees
            employees = Employe.objects.all()
            managers = Manager.objects.all()
            
            stats = {
                'total_employees': 0,
                'total_managers': 0,
                'employees_cleaned': 0,
                'managers_cleaned': 0,
                'total_leaves_forfeited': 0,
            }
            
            # Process employees
            for employee in employees:
                stats['total_employees'] += 1
                
                # Track forfeited leaves
                if employee.carryforward_available_leaves > 0:
                    stats['total_leaves_forfeited'] += employee.carryforward_available_leaves
                    stats['employees_cleaned'] += 1
                
                # Cleanup carryforward
                employee.carryforward_available_leaves = 0
                employee.carryforward_leaves_taken = 0
                
                # Reset if over allocation
                if employee.available_leaves > annual_allocation:
                    employee.available_leaves = annual_allocation
                
                employee.save()
            
            # Process managers
            for manager in managers:
                stats['total_managers'] += 1
                
                # Track forfeited leaves
                if manager.carryforward_available_leaves > 0:
                    stats['total_leaves_forfeited'] += manager.carryforward_available_leaves
                    stats['managers_cleaned'] += 1
                
                # Cleanup carryforward
                manager.carryforward_available_leaves = 0
                manager.carryforward_leaves_taken = 0
                
                # Reset if over allocation
                if manager.available_leaves > annual_allocation:
                    manager.available_leaves = annual_allocation
                
                manager.save()
            
            # Send notification emails
            send_carryforward_cleanup_notification.delay(stats)
            
            logger.info(f"Carryforward cleanup completed successfully. Stats: {stats}")
            return {
                'status': 'success',
                'message': 'Carryforward cleanup completed successfully',
                'stats': stats
            }
            
    except Exception as exc:
        logger.error(f"Carryforward cleanup failed: {exc}")
        # Retry the task
        raise self.retry(exc=exc, countdown=60)


@shared_task
def send_carryforward_reminder():
    """
    Send reminder notification on March 15th about upcoming carryforward cleanup
    """
    try:
        # Get employees and managers with carryforward leaves
        employees_with_carryforward = Employe.objects.filter(carryforward_available_leaves__gt=0)
        managers_with_carryforward = Manager.objects.filter(carryforward_available_leaves__gt=0)
        
        stats = {
            'employees_with_carryforward': employees_with_carryforward.count(),
            'managers_with_carryforward': managers_with_carryforward.count(),
            'total_carryforward_leaves': (
                sum(emp.carryforward_available_leaves for emp in employees_with_carryforward) +
                sum(mgr.carryforward_available_leaves for mgr in managers_with_carryforward)
            ),
            'reminder_date': date.today(),
            'cleanup_date': date(date.today().year, 3, 31),
        }
        
        # Send reminder emails
        send_carryforward_reminder_notification.delay(stats)
        
        logger.info(f"Carryforward reminder sent successfully. Stats: {stats}")
        return {
            'status': 'success',
            'message': 'Carryforward reminder sent successfully',
            'stats': stats
        }
        
    except Exception as exc:
        logger.error(f"Carryforward reminder failed: {exc}")
        return {
            'status': 'error',
            'message': f'Carryforward reminder failed: {exc}'
        }


# ==================== EMAIL NOTIFICATION TASKS ====================

@shared_task
def send_yearly_reset_notification(stats):
    """Send email notification after yearly leave reset"""
    try:
        # Get all founders and managers
        founders = Founder.objects.all()
        managers = Manager.objects.all()

        recipient_emails = []
        recipient_emails.extend([founder.user.email for founder in founders if founder.user.email])
        recipient_emails.extend([manager.user.email for manager in managers if manager.user.email])

        if not recipient_emails:
            logger.warning("No recipient emails found for yearly reset notification")
            return

        # Prepare email context
        context = {
            'stats': stats,
            'reset_date': date.today(),
            'action_url': f"{settings.LEAVE_MANAGEMENT_CONFIG['FRONTEND_BASE_URL']}/managers/leave-summary/",
            'year': date.today().year,
        }

        # Render email template
        html_message = render_to_string('emails/yearly_reset_notification.html', context)
        plain_message = strip_tags(html_message)

        # Send email
        send_mail(
            subject=f"Leave Carryforward Update Required - Year {date.today().year} Reset",
            message=plain_message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=recipient_emails,
            html_message=html_message,
            fail_silently=False
        )

        logger.info(f"Yearly reset notification sent to {len(recipient_emails)} recipients")

    except Exception as exc:
        logger.error(f"Failed to send yearly reset notification: {exc}")


@shared_task
def send_carryforward_cleanup_notification(stats):
    """Send email notification after carryforward cleanup"""
    try:
        # Get all founders and managers
        founders = Founder.objects.all()
        managers = Manager.objects.all()

        recipient_emails = []
        recipient_emails.extend([founder.user.email for founder in founders if founder.user.email])
        recipient_emails.extend([manager.user.email for manager in managers if manager.user.email])

        if not recipient_emails:
            logger.warning("No recipient emails found for carryforward cleanup notification")
            return

        # Prepare email context
        context = {
            'stats': stats,
            'cleanup_date': date.today(),
            'action_url': f"{settings.LEAVE_MANAGEMENT_CONFIG['FRONTEND_BASE_URL']}/managers/leave-summary/",
            'year': date.today().year,
        }

        # Render email template
        html_message = render_to_string('emails/carryforward_cleanup_notification.html', context)
        plain_message = strip_tags(html_message)

        # Send email
        send_mail(
            subject=f"Carryforward Cleanup Completed - March {date.today().year}",
            message=plain_message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=recipient_emails,
            html_message=html_message,
            fail_silently=False
        )

        logger.info(f"Carryforward cleanup notification sent to {len(recipient_emails)} recipients")

    except Exception as exc:
        logger.error(f"Failed to send carryforward cleanup notification: {exc}")


@shared_task
def send_carryforward_reminder_notification(stats):
    """Send reminder email about upcoming carryforward cleanup"""
    try:
        # Get all founders and managers
        founders = Founder.objects.all()
        managers = Manager.objects.all()

        recipient_emails = []
        recipient_emails.extend([founder.user.email for founder in founders if founder.user.email])
        recipient_emails.extend([manager.user.email for manager in managers if manager.user.email])

        if not recipient_emails:
            logger.warning("No recipient emails found for carryforward reminder")
            return

        # Prepare email context
        context = {
            'stats': stats,
            'reminder_date': stats['reminder_date'],
            'cleanup_date': stats['cleanup_date'],
            'action_url': f"{settings.LEAVE_MANAGEMENT_CONFIG['FRONTEND_BASE_URL']}/managers/leave-summary/",
            'year': date.today().year,
        }

        # Render email template
        html_message = render_to_string('emails/carryforward_reminder_notification.html', context)
        plain_message = strip_tags(html_message)

        # Send email
        send_mail(
            subject=f"Reminder: Carryforward Leaves Expire Soon - Action Required",
            message=plain_message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=recipient_emails,
            html_message=html_message,
            fail_silently=False
        )

        logger.info(f"Carryforward reminder notification sent to {len(recipient_emails)} recipients")

    except Exception as exc:
        logger.error(f"Failed to send carryforward reminder notification: {exc}")


# ==================== MANUAL TRIGGER TASKS ====================

@shared_task
def manual_yearly_reset():
    """Manual trigger for yearly leave reset"""
    return yearly_leave_reset.delay()


@shared_task
def manual_carryforward_cleanup():
    """Manual trigger for carryforward cleanup"""
    return carryforward_cleanup.delay()


# ==================== MANAGEMENT COMMAND TASKS ====================

@shared_task
def process_yearly_carryforward_grant():
    """
    Celery task to grant carryforward leaves on December 31st using management command
    This task should be scheduled to run on December 31st at midnight
    """
    try:
        logger.info("Starting yearly carryforward grant process via management command...")

        # Call the management command
        call_command('process_carryforward_leaves', action='grant')

        logger.info("Yearly carryforward grant process completed successfully")
        return "Carryforward leaves granted successfully via management command"

    except Exception as e:
        logger.error(f"Error in yearly carryforward grant process: {e}")
        raise


@shared_task
def process_yearly_carryforward_cleanup():
    """
    Celery task to cleanup carryforward leaves on March 31st using management command
    This task should be scheduled to run on March 31st at midnight
    """
    try:
        logger.info("Starting yearly carryforward cleanup process via management command...")

        # Call the management command
        call_command('process_carryforward_leaves', action='cleanup')

        logger.info("Yearly carryforward cleanup process completed successfully")
        return "Carryforward leaves cleanup completed successfully via management command"

    except Exception as e:
        logger.error(f"Error in yearly carryforward cleanup process: {e}")
        raise


@shared_task
def test_carryforward_system():
    """
    Test task to verify the carryforward system is working
    Can be run manually for testing purposes
    """
    try:
        logger.info("Testing carryforward system via management command...")

        # Call the management command in test mode
        call_command('process_carryforward_leaves', action='test')

        logger.info("Carryforward system test completed successfully")
        return "Carryforward system test completed via management command"

    except Exception as e:
        logger.error(f"Error in carryforward system test: {e}")
        raise
