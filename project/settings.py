import os

from pathlib import Path
from django.utils.timezone import timedelta
from dotenv import load_dotenv

load_dotenv()

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


SECRET_KEY = 'django-insecure-wz5rx#g%l7=r2ij$jq!o+qduhz==&00vq&39b1&hm(_f(snzvd'

DEBUG = True

allowed_hosts_str = os.getenv('ALLOWED_HOSTS')
if allowed_hosts_str:
    allowed_hosts_list = [host.strip() for host in allowed_hosts_str.split(',')]
else:
    allowed_hosts_list = ['localhost', '127.0.0.1']
ALLOWED_HOSTS = allowed_hosts_list



INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'rest_framework',
    'fcm_django',
    'corsheaders',
    'rest_framework.authtoken',
    'rest_framework_simplejwt',

    # Celery apps (commented out until Celery is installed)
    'django_celery_beat',
    'django_celery_results',

        'users',
    'common',
    'managers',
    'employe',
    'leaves',





]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'corsheaders.middleware.CorsMiddleware',
]

ROOT_URLCONF = 'project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': ["templates"],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'common.context_processors.user_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'project.wsgi.application'


DATABASES = {
    'default': {
        'ENGINE':  os.getenv('ENGINE'),
        'NAME': os.getenv('DATABASE_NAME'),
        'HOST': os.getenv('DATABASE_HOST'),
        'USER': os.getenv('DATABASE_USER'),
        'PASSWORD': os.getenv('DATABASE_PASSWORD'),
        'PORT': os.getenv('DATABASE_PORT')
    }
}




AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


LANGUAGE_CODE = 'en-us'

TIME_ZONE =  os.getenv('TIME_ZONE')

USE_I18N = True

USE_TZ = True


PROJECT_MODE = os.environ.get('PROJECT_MODE', 'local')

if PROJECT_MODE == 'production':
    MEDIA_URL = '/media/'
    MEDIA_ROOT = BASE_DIR / "media"
    STATIC_ROOT = BASE_DIR / "staticfiles"
else:
    MEDIA_URL = '/media/'  # ✅ FIX: Remove the comma
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

STATIC_URL = '/static/'  # Also make this consistent with slash
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]


AUTH_USER_MODEL = 'users.User'
AUTH_PROFILE_MODULE = 'users.User'

AUTHENTICATION_BACKENDS = [
    'users.backends.EmailBackend',
    'django.contrib.auth.backends.ModelBackend',
]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.BasicAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ]
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=365),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=365),
}





# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = 'smtp.gmail.com'
# EMAIL_PORT = 587
# EMAIL_USE_TLS = True
# EMAIL_HOST_USER = 'enmav8468@gmail.com'  # Replace with your email
# EMAIL_HOST_PASSWORD = 'hgog lata kbqk dnrb'  # Use App Password if 2FA is enabled

# CORS_ORIGIN_ALLOW_ALL = True

# Fixed: Added complete email configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', 'myemail@gmail.com')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', 'my-app-password')
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER  # Fixed: Added missing DEFAULT_FROM_EMAIL

# ==================== CELERY CONFIGURATION ====================
# Temporarily commented out until Celery is installed

# Celery Configuration Options
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')

# Celery Beat (Scheduler) Configuration
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# Celery Task Configuration
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'

# Celery Worker Configuration
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000

# Celery Results Configuration
CELERY_RESULT_EXPIRES = 3600  # 1 hour

# Task routing
CELERY_TASK_ROUTES = {
    'managers.tasks.*': {'queue': 'leave_management'},
}

# Default queue
CELERY_TASK_DEFAULT_QUEUE = 'default'

# Leave Management Configuration
LEAVE_MANAGEMENT_CONFIG = {
    'ANNUAL_LEAVE_ALLOCATION': 18,
    'MEDICAL_LEAVE_ALLOCATION': 14,
    'CARRYFORWARD_LIMIT': 6,
    'CARRYFORWARD_ELIGIBILITY_THRESHOLD': 10,
    'FRONTEND_BASE_URL': os.getenv('FRONTEND_BASE_URL', 'http://localhost:8000'),
}
