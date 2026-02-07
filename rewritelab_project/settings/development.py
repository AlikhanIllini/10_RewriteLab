"""
Development settings for RewriteLab project.

These settings are for local development only.
Run with: python manage.py runserver --settings=rewritelab_project.settings.development
Or set: export DJANGO_SETTINGS_MODULE=rewritelab_project.settings.development
"""

from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# Allow all hosts in development
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '[::1]']

# Show detailed error pages
INTERNAL_IPS = ['127.0.0.1']

# Email backend for development (prints to console)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Disable password validation in development for easier testing
AUTH_PASSWORD_VALIDATORS = []

# Additional development apps (optional)
# INSTALLED_APPS += ['debug_toolbar']

# Logging configuration for development
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
