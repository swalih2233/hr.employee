# 🎄 Carryforward Leave Management System

## Overview

This system automatically manages carryforward leaves for employees based on the following rules:

### 📋 Business Rules

1. **December 31st Process:**
   - Employees who have taken **≥10 leaves** get **6 carryforward leaves**
   - Carryforward leaves are valid until March 31st
   - Email notifications sent to managers and founders

2. **March 31st Process:**
   - All unused carryforward leaves are automatically removed
   - `carryforward_available_leaves = 0`
   - `carryforward_leaves_taken = 0`
   - Email notifications sent about cleanup

## 🚀 Quick Start

### 1. Test the System

```bash
# Test without making changes
python manage.py process_carryforward_leaves --action=test --dry-run

# Test grant process
python manage.py process_carryforward_leaves --action=grant --dry-run

# Test cleanup process
python manage.py process_carryforward_leaves --action=cleanup --dry-run
```

### 2. Manual Execution

```bash
# Grant carryforward leaves (run on Dec 31st)
python manage.py process_carryforward_leaves --action=grant

# Cleanup carryforward leaves (run on Mar 31st)
python manage.py process_carryforward_leaves --action=cleanup
```

## 🔧 Automation Options

### Option 1: Cron Jobs (Recommended for Simple Setups)

Add to your crontab (`crontab -e`):

```bash
# Grant carryforward leaves on December 31st at midnight
0 0 31 12 * cd /path/to/your/project && python manage.py process_carryforward_leaves --action=grant

# Cleanup carryforward leaves on March 31st at midnight
0 0 31 3 * cd /path/to/your/project && python manage.py process_carryforward_leaves --action=cleanup

# Optional: Daily health check at 2 AM
0 2 * * * cd /path/to/your/project && python manage.py process_carryforward_leaves --action=test --dry-run
```

### Option 2: Celery Beat (Recommended for Production)

1. **Install Celery:**
   ```bash
   pip install celery redis
   ```

2. **Add to settings.py:**
   ```python
   # Import the schedule configuration
   from .celery_schedule import *
   ```

3. **Start services:**
   ```bash
   # Start Redis
   redis-server
   
   # Start Celery worker
   celery -A project worker -l info
   
   # Start Celery beat scheduler
   celery -A project beat -l info
   ```

### Option 3: APScheduler (Alternative to Celery)

1. **Install APScheduler:**
   ```bash
   pip install apscheduler
   ```

2. **Add to your app's apps.py:**
   ```python
   from django.apps import AppConfig
   
   class ManagersConfig(AppConfig):
       default_auto_field = 'django.db.models.BigAutoField'
       name = 'managers'
       
       def ready(self):
           from .scheduler import start_scheduler
           start_scheduler()
   ```

## 📧 Email Notifications

The system sends HTML email notifications to:
- **Managers** - about their team's carryforward status
- **Founders** - comprehensive reports with statistics

### Email Templates Include:
- Employee eligibility summary
- Carryforward leave allocations
- Important dates and deadlines
- Action buttons for easy access

## 🧪 Testing

### Test Current Data

```bash
# See what would happen with current employee data
python test_carryforward_command.py
```

### Manual Testing

```python
# In Django shell
python manage.py shell

>>> from managers.tasks import test_carryforward_system
>>> test_carryforward_system()

# Or test specific functions
>>> from managers.scheduler import trigger_carryforward_grant
>>> trigger_carryforward_grant()
```

## 📊 Monitoring

### Check Scheduled Jobs (APScheduler)

```python
from managers.scheduler import list_scheduled_jobs
jobs = list_scheduled_jobs()
for job in jobs:
    print(f"{job['name']}: {job['next_run']}")
```

### Check Celery Tasks

```bash
# Check active tasks
celery -A project inspect active

# Check scheduled tasks
celery -A project inspect scheduled
```

## 🔍 Troubleshooting

### Common Issues

1. **Command not found:**
   - Ensure you're in the correct directory
   - Check that the management command file exists

2. **Email not sending:**
   - Verify email settings in Django settings
   - Check that managers/founders have email addresses

3. **Scheduler not starting:**
   - Check logs for error messages
   - Ensure required packages are installed

### Debug Mode

```bash
# Run with verbose output
python manage.py process_carryforward_leaves --action=test --dry-run --verbosity=2
```

## 📁 File Structure

```
managers/
├── management/
│   └── commands/
│       └── process_carryforward_leaves.py  # Main command
├── tasks.py                                # Celery tasks
├── scheduler.py                            # APScheduler setup
└── ...

scripts/
└── carryforward_cron.sh                   # Cron script

celery_schedule.py                          # Celery configuration
CARRYFORWARD_SETUP.md                      # This documentation
```

## 🎯 Key Features

✅ **Automated Processing** - Runs on schedule without manual intervention
✅ **Dry Run Mode** - Test without making changes
✅ **Email Notifications** - HTML emails with detailed information
✅ **Error Handling** - Comprehensive logging and error recovery
✅ **Multiple Scheduling Options** - Cron, Celery, or APScheduler
✅ **Manual Testing** - Easy testing and debugging tools
✅ **Production Ready** - Robust and scalable implementation

## 🔐 Security Considerations

- All operations are logged for audit trails
- Dry run mode prevents accidental changes
- Email notifications include security headers
- Database transactions ensure data consistency

## 📈 Performance

- Batch processing for efficiency
- Database queries are optimized
- Email sending is asynchronous (with Celery)
- Minimal resource usage

## 🆘 Support

For issues or questions:
1. Check the logs in your project's log directory
2. Run the test command to verify system status
3. Review the email notifications for any error messages

---

**Last Updated:** December 2024
**Version:** 1.0.0
