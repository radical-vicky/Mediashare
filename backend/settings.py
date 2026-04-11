"""
Django settings for backend project.
"""

from pathlib import Path
from decouple import config
import os
import dj_database_url
import cloudinary
import cloudinary.uploader
import cloudinary.api

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='django-insecure-y*y(t(yg6blp%6&f6*-j688zbdd0y#8h-i3qe11-684@cltox^')
DEBUG = config('DEBUG', default=False, cast=bool)

# ALLOWED_HOSTS - Updated for Render
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1,vibegaze.onrender.com,.onrender.com').split(',')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    
    # Third-party apps
    'channels',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    
    # Cloudinary apps - MUST be before 'frontend'
    'cloudinary_storage',
    'cloudinary',
    
    'frontend',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Must be first after SecurityMiddleware
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]

ROOT_URLCONF = 'backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'frontend.context_processors.unread_messages_count',
                'frontend.context_processors.background_media',
            ],
        },
    },
]

WSGI_APPLICATION = 'backend.wsgi.application'
ASGI_APPLICATION = 'backend.asgi.application'

# Channels configuration
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}

# Database - Use PostgreSQL on Render, fallback to SQLite locally
DATABASES = {
    'default': dj_database_url.config(
        default='sqlite:///' + str(BASE_DIR / 'db.sqlite3'),
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# Password validation
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

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# ========== STATIC FILES CONFIGURATION ==========
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# WhiteNoise configuration for static files
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ========== MEDIA FILES & CLOUDINARY CONFIGURATION ==========
# Get credentials from environment variables (set these in Render)
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.environ.get('CLOUDINARY_CLOUD_NAME', 'dvuooxbqi'),
    'API_KEY': os.environ.get('CLOUDINARY_API_KEY', '875143959481713'),
    'API_SECRET': os.environ.get('CLOUDINARY_API_SECRET', ''),
}

# Configure cloudinary
cloudinary.config(
    cloud_name=CLOUDINARY_STORAGE['CLOUD_NAME'],
    api_key=CLOUDINARY_STORAGE['API_KEY'],
    api_secret=CLOUDINARY_STORAGE['API_SECRET'],
    secure=True
)

# Media files - Use Cloudinary for storage
MEDIA_URL = '/media/'
DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

# ========== FILE UPLOAD SETTINGS ==========
DATA_UPLOAD_MAX_MEMORY_SIZE = None
DATA_UPLOAD_MAX_NUMBER_FIELDS = None
DATA_UPLOAD_MAX_NUMBER_FILES = None
REQUEST_TIMEOUT = 3600
FILE_UPLOAD_HANDLERS = [
    'django.core.files.uploadhandler.TemporaryFileUploadHandler',
]
FILE_UPLOAD_MAX_MEMORY_SIZE = 2621440
FILE_UPLOAD_TEMP_DIR = None
CHUNKED_UPLOAD_MAX_FILE_SIZE = None
CHUNKED_UPLOAD_MAX_CHUNK_SIZE = None

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ========== DJANGO-ALLAUTH CONFIGURATION ==========
SITE_ID = 1

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

ACCOUNT_LOGIN_METHODS = {'username', 'email'}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'username*', 'password1*', 'password2*']
ACCOUNT_RATE_LIMITS = {
    'login_failed': '5/5m',
}
ACCOUNT_EMAIL_VERIFICATION = 'none'
ACCOUNT_LOGOUT_ON_GET = True
ACCOUNT_LOGOUT_REDIRECT_URL = '/'
ACCOUNT_SESSION_REMEMBER = True
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_LOGIN_ON_PASSWORD_RESET = True
ACCOUNT_USERNAME_MIN_LENGTH = 3

# Email configuration
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'webmaster@localhost'
EMAIL_SUBJECT_PREFIX = '[MediaShare] '

# ========== TWILIO CONFIGURATION ==========
TWILIO_ACCOUNT_SID = config('TWILIO_ACCOUNT_SID', default='')
TWILIO_AUTH_TOKEN = config('TWILIO_AUTH_TOKEN', default='')
TWILIO_PHONE_NUMBER = config('TWILIO_PHONE_NUMBER', default='')

# ========== CSRF SETTINGS ==========
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:8000',
    'http://127.0.0.1:8000',
    'https://vibegaze.onrender.com',
    'https://*.onrender.com',
]
CSRF_COOKIE_NAME = 'csrftoken'
CSRF_COOKIE_AGE = 31449600
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_HTTPONLY = False
CSRF_USE_SESSIONS = False

# ========== SECURITY SETTINGS ==========
SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin'
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# ========== MPESA CONFIGURATION ==========
MPESA_CONSUMER_KEY = os.environ.get('MPESA_CONSUMER_KEY', '')
MPESA_CONSUMER_SECRET = os.environ.get('MPESA_CONSUMER_SECRET', '')
MPESA_SHORTCODE = os.environ.get('MPESA_SHORTCODE', '174379')
MPESA_SHORTCODE_TYPE = os.environ.get('MPESA_SHORTCODE_TYPE', 'paybill')
MPESA_PASSKEY = os.environ.get('MPESA_PASSKEY', '')
MPESA_CALLBACK_URL = os.environ.get('MPESA_CALLBACK_URL', 'https://vibegaze.onrender.com/mpesa/callback/')
MPESA_ENVIRONMENT = os.environ.get('MPESA_ENVIRONMENT', 'sandbox')
MPESA_INITIATOR_NAME = os.environ.get('MPESA_INITIATOR_NAME', 'testapi')
MPESA_INITIATOR_PASSWORD = os.environ.get('MPESA_INITIATOR_PASSWORD', '')
