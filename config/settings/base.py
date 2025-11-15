"""
KALPÉ SANTÉ - Base Settings
Production-ready Django configuration following security best practices.
This file contains settings common to all environments.
"""

import os
from pathlib import Path
from decouple import config, Csv
from datetime import timedelta

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())

# Environment
ENVIRONMENT = config('ENVIRONMENT', default='development')

# Timezone and Language
TIME_ZONE = 'Africa/Dakar'
LANGUAGE_CODE = 'fr-fr'
USE_I18N = True
USE_TZ = True

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom user model
AUTH_USER_MODEL = 'users.User'

# Sites Framework
SITE_ID = 1

DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
     'django.contrib.sites',
    'django.contrib.humanize',
    'django.contrib.admindocs',
    # swagger
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'corsheaders',
    'django_filters',
    'django_extensions',
    'drf_yasg',
    'rest_framework_simplejwt',
    'drf_spectacular',
    'drf_spectacular_sidecar',
]

CUSTOM_APPS = [
    'apps.core',
    'apps.users',
    'apps.wallet',
    'apps.healthcare', 
    'apps.pharmacy',
    'apps.payments',
    'apps.analytics',
    'apps.notifications',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + CUSTOM_APPS

MIDDLEWARE = [
    # Security (should be first)
    'django.middleware.security.SecurityMiddleware',
    
    # Sessions
    'django.contrib.sessions.middleware.SessionMiddleware',
    
    # CORS (before CommonMiddleware)
    'corsheaders.middleware.CorsMiddleware',
    
    # Django core
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    
    # Custom middleware (will be created)
    # 'apps.core.middleware.AuditMiddleware',
    # 'apps.core.middleware.RequestLoggingMiddleware',
]

ROOT_URLCONF = 'config.urls'

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
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 12,  # NIST SP 800-63B recommendation for health data
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTH_USER_MODEL = 'users.User'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.MultiPartParser',
        'rest_framework.parsers.FormParser',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'MAX_PAGE_SIZE': 100,
    
    # Throttling for security
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': config('RATE_LIMIT_ANONYMOUS', default='30/min'),
        'user': config('RATE_LIMIT_AUTHENTICATED', default='100/min'),
        'admin': config('RATE_LIMIT_ADMIN', default='1000/min'),
    },
    
    # Schema generation
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    
    # Versioning
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.URLPathVersioning',
    'DEFAULT_VERSION': 'v1',
    'ALLOWED_VERSIONS': ['v1', 'v2'],
    
    # Exception handling
    # 'EXCEPTION_HANDLER': 'apps.core.exceptions.custom_exception_handler',
}
SIMPLE_JWT = {
    # ⏳ Access token valable 1 heure
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    
    # 🔄 Refresh token valable 7 jours
    'REFRESH_TOKEN_LIFETIME': timedelta(days=config('JWT_REFRESH_TOKEN_LIFETIME', default=7, cast=int)),
    
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    
    'TOKEN_TYPE_CLAIM': 'token_type',
    'JTI_CLAIM': 'jti',
}

CORS_ALLOWED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    
]

SPECTACULAR_SETTINGS = {
    'TITLE': 'KALPÉ SANTÉ API',
    'DESCRIPTION': 'API pour la plateforme solidaire de financement des soins de santé',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'SWAGGER_UI_DIST': 'SIDECAR',
    'SWAGGER_UI_FAVICON_HREF': 'SIDECAR',
    'REDOC_DIST': 'SIDECAR',
    'COMPONENT_SPLIT_REQUEST': True,
    'SORT_OPERATIONS': False,
    'SCHEMA_PATH_PREFIX': '/api/v[0-9]',
    'TAGS': [
        {'name': 'Authentication', 'description': 'Endpoints d\'authentification'},
        {'name': 'Users', 'description': 'Gestion des utilisateurs multi-rôles'},
        {'name': 'Wallet', 'description': 'Portefeuille électronique et transactions'},
        {'name': 'Healthcare', 'description': 'Dossiers médicaux, tickets santé, ordonnances'},
        {'name': 'Pharmacy', 'description': 'Pharmacies, médicaments et stock'},
        {'name': 'Payments', 'description': 'Paiements et intégrations (Orange Money, Wave)'},
        {'name': 'Analytics', 'description': 'Rapports, dashboards et statistiques'},
        {'name': 'Notifications', 'description': 'Notifications SMS, Email, Push'},
    ],
}

# CORS Configuration - More secure than ALLOW_ALL
CORS_ALLOW_ALL_ORIGINS = DEBUG  # Only in development
if not DEBUG:
    CORS_ALLOWED_ORIGINS = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]
CORS_ALLOW_CREDENTIALS = True

# Security Headers (Production)
SECURE_SSL_REDIRECT = not DEBUG
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0  # 1 year in production
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

# Session Security
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 86400  # 1 day

CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'

# Business Logic Constants
MIN_TRANSACTION_AMOUNT = config('MIN_TRANSACTION_AMOUNT', default=100, cast=int)
MAX_TRANSACTION_AMOUNT = config('MAX_TRANSACTION_AMOUNT', default=1000000, cast=int)
DAILY_TRANSACTION_LIMIT = config('DAILY_TRANSACTION_LIMIT', default=5000000, cast=int)
DEFAULT_CURRENCY = config('DEFAULT_CURRENCY', default='XOF')

# Feature Flags
ENABLE_MFA = config('ENABLE_MFA', default=True, cast=bool)
ENABLE_EMAIL_VERIFICATION = config('ENABLE_EMAIL_VERIFICATION', default=True, cast=bool)
ENABLE_SMS_NOTIFICATIONS = config('ENABLE_SMS_NOTIFICATIONS', default=True, cast=bool)
ENABLE_FRAUD_DETECTION = config('ENABLE_FRAUD_DETECTION', default=True, cast=bool)
ENABLE_AUDIT_LOGGING = config('ENABLE_AUDIT_LOGGING', default=True, cast=bool)

# Compliance Settings
DATA_RETENTION_DAYS = config('DATA_RETENTION_DAYS', default=2555, cast=int)  # 7 years for health data
ANONYMIZE_DELETED_USERS = config('ANONYMIZE_DELETED_USERS', default=True, cast=bool)

# ==============================================================================
# CELERY CONFIGURATION
# ==============================================================================

# Celery broker URL - uses Redis by default, fallback to in-memory for development
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://localhost:6379/0')

# For development without Redis/RabbitMQ, use eager mode (synchronous execution)
CELERY_TASK_ALWAYS_EAGER = config('CELERY_TASK_ALWAYS_EAGER', default=DEBUG, cast=bool)
CELERY_TASK_EAGER_PROPAGATES = True

# Celery task settings
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60  # 25 minutes

# Celery beat schedule (periodic tasks)
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
