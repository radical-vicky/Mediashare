"""
Django settings for backend project.
"""

from pathlib import Path
from decouple import config
import os
import dj_database_url

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='django-insecure-y*y(t(yg6blp%6&f6*-j688zbdd0y#8h-i3qe11-684@cltox^')
DEBUG = config('DEBUG', default=False, cast=bool)  # Changed to False for production

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
    
    'frontend',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Added WhiteNoise for static files
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

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# WhiteNoise configuration for static files
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ========== FILE UPLOAD SETTINGS - NO LIMITS ==========

# Remove all size limits
DATA_UPLOAD_MAX_MEMORY_SIZE = None  # No memory limit
DATA_UPLOAD_MAX_NUMBER_FIELDS = None  # No field limit
DATA_UPLOAD_MAX_NUMBER_FILES = None  # No file limit

# Increase timeout for large file uploads (in seconds)
REQUEST_TIMEOUT = 3600  # 1 hour timeout

# File upload handlers - use temporary file handler for large files
FILE_UPLOAD_HANDLERS = [
    'django.core.files.uploadhandler.TemporaryFileUploadHandler',
]

# Large file upload settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 2621440  # 2.5MB before writing to disk
FILE_UPLOAD_TEMP_DIR = None  # Use system temp directory

# Chunked upload settings (for very large files)
CHUNKED_UPLOAD_MAX_FILE_SIZE = None  # No limit
CHUNKED_UPLOAD_MAX_CHUNK_SIZE = None  # No chunk limit

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

# HTTPS settings (for production on Render)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = False  # Render handles HTTPS automatically
SESSION_COOKIE_SECURE = True  # Only send cookies over HTTPS
CSRF_COOKIE_SECURE = True  # Only send CSRF cookies over HTTPS

# ========== MPESA CONFIGURATION ==========
MPESA_CONSUMER_KEY = os.environ.get('MPESA_CONSUMER_KEY', 'LQost6BhC09UpLKaYjbRunq3IZN1ylfzHzI8tz47jxlaVHvI')
MPESA_CONSUMER_SECRET = os.environ.get('MPESA_CONSUMER_SECRET', 'Kn2l7P0mCnFAJAi7KdOMsIRkpAsH698PBLbhG5EqVRc7CY27pv6d0U96hEhmByo6')
MPESA_SHORTCODE = os.environ.get('MPESA_SHORTCODE', '174379')
MPESA_SHORTCODE_TYPE = os.environ.get('MPESA_SHORTCODE_TYPE', 'paybill')
MPESA_PASSKEY = os.environ.get('MPESA_PASSKEY', 'bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919')
MPESA_CALLBACK_URL = os.environ.get('MPESA_CALLBACK_URL', 'https://vibegaze.onrender.com/mpesa/callback/')
MPESA_ENVIRONMENT = os.environ.get('MPESA_ENVIRONMENT', 'sandbox')
MPESA_INITIATOR_NAME = os.environ.get('MPESA_INITIATOR_NAME', 'testapi')
MPESA_INITIATOR_PASSWORD = os.environ.get('MPESA_INITIATOR_PASSWORD', 'Safaricom2018')
