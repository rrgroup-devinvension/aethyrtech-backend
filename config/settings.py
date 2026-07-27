from pathlib import Path
from dotenv import load_dotenv
import os
from corsheaders.defaults import default_headers

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("SECRET_KEY")
DEBUG = os.getenv("DEBUG", "False") == "True"

ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "").split(",")

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'django_filters',
    'drf_spectacular',
    
    # Global Utilities
    'shared',
    'scripts',
    
    # Core Cloud
    'core.analytics',
    'core.authentication',
    'core.categories',
    'core.llm_providers',
    'core.organizations',
    'core.users',
    
    # Experience Cloud
    'experience_cloud.analytics',
    'experience_cloud.api_provider',
    'experience_cloud.catalog',
    'experience_cloud.executions',
    'experience_cloud.json_generator',
    'experience_cloud.market_data',
    'experience_cloud.market_integrations',
    
    # Identity & Media Clouds (Roots)
    'identity_cloud',
    'media_cloud',


]

REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "shared.pagination.StandardResultsSetPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_RENDERER_CLASSES": (
        "shared.response.StandardJSONRenderer",
    ),
    "EXCEPTION_HANDLER": "shared.exceptions.custom_exception_handler",
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
}

CORS_ALLOWED_ORIGINS = [
    "http://localhost:4200",
]
CORS_ALLOW_HEADERS = list(default_headers) + [
    "noauth",
]

CORS_EXPOSE_HEADERS = [
    "Content-Disposition",
]

from datetime import timedelta

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,

    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "VERIFYING_KEY": None,
    "AUDIENCE": None,
    "ISSUER": None,

    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",

    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "TOKEN_TYPE_CLAIM": "token_type",

    "JTI_CLAIM": "jti",
}


MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "shared.middlewares.RequestLogMiddleware",
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    "shared.middlewares.IdempotencyMiddleware",
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv("DB_NAME"),
        'USER': os.getenv("DB_USER"),
        'PASSWORD': os.getenv("DB_PASSWORD"),
        'HOST': os.getenv("DB_HOST"),
        'PORT': os.getenv("DB_PORT"),
    },
    'xbytes_db': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv("XBYTES_DB_NAME", "xbytesdata"),
        'USER': os.getenv("XBYTES_DB_USER", os.getenv("DB_USER")),
        'PASSWORD': os.getenv("XBYTES_DB_PASSWORD", os.getenv("DB_PASSWORD")),
        'HOST': os.getenv("XBYTES_DB_HOST", os.getenv("DB_HOST")),
        'PORT': os.getenv("XBYTES_DB_PORT", os.getenv("DB_PORT")),
        'CONN_MAX_AGE': int(os.getenv("EXTERNAL_DB_CONN_MAX_AGE", 300)),
        'OPTIONS': {
            'connect_timeout': int(os.getenv("EXTERNAL_DB_CONNECT_TIMEOUT", 10)),
        }
    },
    'karmatech_db': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv("KARMATECH_DB_NAME", "karmatechdata"),
        'USER': os.getenv("KARMATECH_DB_USER", os.getenv("DB_USER")),
        'PASSWORD': os.getenv("KARMATECH_DB_PASSWORD", os.getenv("DB_PASSWORD")),
        'HOST': os.getenv("KARMATECH_DB_HOST", os.getenv("DB_HOST")),
        'PORT': os.getenv("KARMATECH_DB_PORT", os.getenv("DB_PORT")),
        'CONN_MAX_AGE': int(os.getenv("EXTERNAL_DB_CONN_MAX_AGE", 300)),
        'OPTIONS': {
            'connect_timeout': int(os.getenv("EXTERNAL_DB_CONNECT_TIMEOUT", 10)),
        }
    }
}

DATABASE_ROUTERS = [
    'experience_cloud.market_integrations.routers.ExternalDBRouter',
    'config.routers.XBytesDataRouter'
]


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

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

STATIC_URL = 'static/'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'core_users.User'

# ============================================================================
# Celery Configuration
# ============================================================================
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60


EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')

# ============================================================================
# Caching (Redis)
# ============================================================================
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.getenv("REDIS_URL", "redis://localhost:6379/1"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}

# ============================================================================
# API Documentation (DRF Spectacular)
# ============================================================================
SPECTACULAR_SETTINGS = {
    'TITLE': 'Aethyrtech API',
    'DESCRIPTION': 'Domain-Driven API for Aethyrtech Cloud',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

# ============================================================================
# Logging Configuration
# ============================================================================
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} [{module}] {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
        'simple': {
            'format': '[{asctime}] {levelname} {message}',
            'style': '{',
            'datefmt': '%H:%M:%S'
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file_info': {
            'level': 'INFO',
            'class': 'concurrent_log_handler.ConcurrentRotatingFileHandler',
            'filename': os.path.join(LOGS_DIR, 'django_info.log'),
            'maxBytes': 1024 * 1024 * 10,  # 10 MB limit per file
            'backupCount': 5,  # Keep up to 5 backups
            'formatter': 'verbose',
        },
        'file_error': {
            'level': 'ERROR',
            'class': 'concurrent_log_handler.ConcurrentRotatingFileHandler',
            'filename': os.path.join(LOGS_DIR, 'django_error.log'),
            'maxBytes': 1024 * 1024 * 10,  # 10 MB limit per file
            'backupCount': 5,  # Keep up to 5 backups
            'formatter': 'verbose',
        },
        'market_data_file': {
            'level': 'INFO',
            'class': 'concurrent_log_handler.ConcurrentRotatingFileHandler',
            'filename': os.path.join(LOGS_DIR, 'market_data.log'),
            'maxBytes': 1024 * 1024 * 10,  # 10 MB limit per file
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'json_generator_file': {
            'level': 'INFO',
            'class': 'concurrent_log_handler.ConcurrentRotatingFileHandler',
            'filename': os.path.join(LOGS_DIR, 'json_generator.log'),
            'maxBytes': 1024 * 1024 * 10,
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file_info', 'file_error'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['console', 'file_info', 'file_error'],
            'level': 'INFO',
            'propagate': False, # Prevent duplicate logging in 'django'
        },
        'experience_cloud.market_data': {
            'handlers': ['console', 'market_data_file', 'file_error'],
            'level': 'INFO',
            'propagate': False,
        },
        'experience_cloud.market_integrations': {
            'handlers': ['console', 'market_data_file', 'file_error'],
            'level': 'INFO',
            'propagate': False,
        },
        'experience_cloud.json_generator': {
            'handlers': ['console', 'json_generator_file', 'file_error'],
            'level': 'INFO',
            'propagate': False,
        },
        # Catch-all for any other custom loggers in your apps
        '': {
            'handlers': ['console', 'file_info', 'file_error'],
            'level': 'INFO',
        }
    },
}

