# Automated Leave Management with Celery

This document provides comprehensive setup instructions for the automated leave management system using Celery.

## 📋 Overview

The system automatically handles:
- **December 31st**: Yearly leave reset with carryforward calculation
- **March 15th**: Carryforward reminder notifications
- **March 31st**: Carryforward cleanup and expiration

## 🚀 Quick Setup

### 1. Install Dependencies

```bash
pip install -r requirements_celery.txt
```

### 2. Install and Start Redis (Broker)

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

**macOS:**
```bash
brew install redis
brew services start redis
```

**Windows:**
Download and install Redis from: https://github.com/microsoftarchive/redis/releases

### 3. Environment Variables

Add to your `.env` file:
```env
# Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Frontend URL for email buttons
FRONTEND_BASE_URL=http://localhost:8000

# Email Configuration (required for notifications)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

### 4. Database Migration

```bash
python manage.py migrate
```

### 5. Setup Celery Beat Tasks

```bash
python manage.py setup_celery_beat
```

### 6. Start Celery Services

**Terminal 1 - Start Celery Worker:**
```bash
celery -A project worker -l info
```

**Terminal 2 - Start Celery Beat (Scheduler):**
```bash
celery -A project beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

**Terminal 3 - Start Django Development Server:**
```bash
python manage.py runserver
```

## 📅 Automated Schedule

| Task | Schedule | Description |
|------|----------|-------------|
| Yearly Leave Reset | Dec 31, 11:59 PM | Reset annual/medical leaves, calculate carryforward |
| Carryforward Reminder | Mar 15, 9:00 AM | Send reminder about upcoming expiration |
| Carryforward Cleanup | Mar 31, 11:59 PM | Remove expired carryforward leaves |

## 🔧 Manual Controls

### Founder Dashboard Access
- Navigate to `/managers/leave-summary/`
- Manual trigger buttons for founders only
- Export leave data to CSV
- View Celery task status at `/managers/celery-status/`

### Admin Interface
- Access Django admin at `/admin/`
- Manage periodic tasks in "Django Celery Beat" section
- Bulk actions for leave management
- View task execution history

### Management Commands

**Reset Celery Beat tasks:**
```bash
python manage.py setup_celery_beat --reset
```

**Manual task triggers (via Django shell):**
```python
from managers.tasks import yearly_leave_reset, carryforward_cleanup

# Trigger yearly reset
yearly_leave_reset.delay()

# Trigger carryforward cleanup
carryforward_cleanup.delay()
```

## 📧 Email Notifications

### Templates Location
- `templates/emails/yearly_reset_notification.html`
- `templates/emails/carryforward_cleanup_notification.html`
- `templates/emails/carryforward_reminder_notification.html`

### Recipients
- All Founders (for all notifications)
- All Managers (for all notifications)

### Email Content
- Summary statistics
- Action buttons linking to leave summary
- Detailed information about changes
- Next steps and deadlines

## 🔍 Monitoring and Troubleshooting

### Check Celery Status
```bash
# Check if Redis is running
redis-cli ping

# Check Celery worker status
celery -A project inspect active

# Check scheduled tasks
celery -A project inspect scheduled
```

### View Logs
```bash
# Celery worker logs
celery -A project worker -l debug

# Celery beat logs
celery -A project beat -l debug
```

### Common Issues

**1. Redis Connection Error**
- Ensure Redis is running: `redis-cli ping`
- Check CELERY_BROKER_URL in settings

**2. Tasks Not Executing**
- Verify Celery Beat is running
- Check periodic tasks in Django admin
- Ensure tasks are enabled

**3. Email Not Sending**
- Verify EMAIL_* settings in .env
- Check email credentials
- Test with Django shell: `python manage.py shell`

**4. Permission Errors**
- Ensure proper user roles (Founder/Manager)
- Check decorators on views
- Verify user authentication

## 🏗️ Production Deployment

### Using Supervisor (Recommended)

**1. Install Supervisor:**
```bash
sudo apt install supervisor
```

**2. Create Celery Worker Config:**
```ini
# /etc/supervisor/conf.d/celery_worker.conf
[program:celery_worker]
command=/path/to/venv/bin/celery -A project worker -l info
directory=/path/to/project
user=www-data
numprocs=1
stdout_logfile=/var/log/celery/worker.log
stderr_logfile=/var/log/celery/worker.log
autostart=true
autorestart=true
startsecs=10
stopwaitsecs=600
killasgroup=true
priority=998
```

**3. Create Celery Beat Config:**
```ini
# /etc/supervisor/conf.d/celery_beat.conf
[program:celery_beat]
command=/path/to/venv/bin/celery -A project beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
directory=/path/to/project
user=www-data
numprocs=1
stdout_logfile=/var/log/celery/beat.log
stderr_logfile=/var/log/celery/beat.log
autostart=true
autorestart=true
startsecs=10
stopwaitsecs=600
killasgroup=true
priority=999
```

**4. Start Services:**
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start celery_worker
sudo supervisorctl start celery_beat
```

### Using Docker

**docker-compose.yml:**
```yaml
version: '3.8'
services:
  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
  
  celery_worker:
    build: .
    command: celery -A project worker -l info
    depends_on:
      - redis
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
  
  celery_beat:
    build: .
    command: celery -A project beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
    depends_on:
      - redis
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
```

## 🧪 Testing

### Test Email Notifications
```python
# Django shell
from managers.tasks import send_yearly_reset_notification

# Test with sample data
stats = {
    'total_employees': 10,
    'total_managers': 3,
    'employees_with_carryforward': 5,
    'managers_with_carryforward': 2,
    'total_carryforward_leaves': 42
}

send_yearly_reset_notification.delay(stats)
```

### Test Leave Reset Logic
```python
# Django shell
from managers.tasks import yearly_leave_reset

# Run in test mode (check logs)
result = yearly_leave_reset.delay()
print(result.get())
```

## 📊 Configuration Options

### Leave Management Settings
```python
# settings.py
LEAVE_MANAGEMENT_CONFIG = {
    'ANNUAL_LEAVE_ALLOCATION': 18,
    'MEDICAL_LEAVE_ALLOCATION': 14,
    'CARRYFORWARD_LIMIT': 6,
    'CARRYFORWARD_ELIGIBILITY_THRESHOLD': 10,
    'FRONTEND_BASE_URL': 'https://your-domain.com',
}
```

### Celery Settings
```python
# settings.py
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
CELERY_TIMEZONE = 'UTC'
```

## 🔐 Security Considerations

1. **Redis Security**: Use password authentication in production
2. **Email Credentials**: Use app passwords, not account passwords
3. **Access Control**: Ensure only founders can trigger manual resets
4. **Logging**: Monitor task execution and failures
5. **Backup**: Regular database backups before major operations

## 📞 Support

For issues or questions:
1. Check logs in `/var/log/celery/` (production)
2. Review Django admin for task status
3. Use the Celery status dashboard at `/managers/celery-status/`
4. Test individual components in Django shell

---

**Last Updated**: {{ current_date }}
**Version**: 1.0.0
