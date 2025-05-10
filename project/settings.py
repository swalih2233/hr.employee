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
allowed_hosts_list = allowed_hosts_str.split(',')
allowed_hosts_list = [host.strip() for host in allowed_hosts_list]
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

    'users',
    'common',
    'managers',
    'employe',
    


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
    MEDIA_ROOT = BASE_DIR / "media"
    STATIC_ROOT = os.path.join(BASE_DIR, 'static')
else:
    MEDIA_ROOT = BASE_DIR / "media"
    STATICFILES_DIRS = [BASE_DIR / "static"]

STATIC_URL = 'static/'
MEDIA_URL = '/media/'


AUTH_USER_MODEL = 'users.User'
AUTH_PROFILE_MODULE = 'users.User'

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

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS') == 'True'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')