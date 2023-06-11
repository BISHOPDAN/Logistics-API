from datetime import timedelta
from decouple import config
import os
from pathlib import Path
from corsheaders.defaults import default_headers

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config('SECRET_KEY')
ENCRYPTING_KEY = config('ENCRYPTING_KEY')

DEBUG = config('DEBUG', default=False, cast=bool)

INTERNAL_IPS = [
    "127.0.0.1",
]


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    "corsheaders",
    'drf_yasg',

    # neccesary for postgres full text search
    'django.contrib.postgres',

    'account',
    'project_api_key',
    'payment',
    'cargo',
    'transport',
    "debug_toolbar",

    # new apps
    # 'testimonials',
    # 'locations',
    # 'newsletter',
    # 'logistics',
]

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),

    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTTokenUserAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ),

    'DEFAULT_PAGINATION_CLASS': 'utils.base.pagination.CustomPagination',

    'DEFAULT_RENDERER_CLASSES': (
        'utils.base.renderer.ApiRenderer',
    ),
}

API_KEY_HEADER = "HTTP_BEARER_API_KEY"
API_SEC_KEY_HEADER = "HTTP_BEARER_SEC_API_KEY"

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    "debug_toolbar.middleware.DebugToolbarMiddleware",
]


CORS_ORIGIN_ALLOW_ALL = True
CORS_ALLOW_ALL_ORIGINS = True

CORS_ALLOW_HEADERS = list(default_headers) + [
    "Bearer-Api-Key",
    "Bearer-Sec-Api-Key",
]


SWAGGER_SETTINGS = {
    'DEFAULT_AUTO_SCHEMA_CLASS': 'utils.base.schema.BaseSchema',
    'APIS_SORTER': 'alpha',
    'JSON_EDITOR': True,
    "SECURITY_DEFINITIONS": {
        "JWT [Bearer {TOKEN}]": {
            "name": "Authorization",
            "type": "apiKey",
            "in": "header",
        },
        "API KEY": {
            "name": "Bearer-Api-Key",
            "type": "apiKey",
            "in": "header",
        },
        "Secret KEY": {
            "name": "Bearer-Sec-Api-Key",
            "type": "apiKey",
            "in": "header",
        },
        "Basic": {
            "type": "basic",
            "name": "Authorization",
        }
    },
}

ROOT_URLCONF = 'tripapi.urls'
AUTH_USER_MODEL = 'account.User'
WSGI_APPLICATION = 'tripapi.wsgi.application'

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

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',  # noqa
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',  # noqa
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',  # noqa
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',  # noqa
    },
]


CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379',
    }
}


LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': config("DB_NAME", default=''),
        'USER': config("DB_USER", default=''),
        'PASSWORD': config("DB_PASSWORD", default=''),
        'HOST': 'localhost',
        'PORT': '',
    }
}


STATIC_URL = '/static/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

MEDIA_ROOT = BASE_DIR / "media"
MEDIA_URL = '/media/'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'loggers': {
        'basic': {
            'handlers': ['basic_h'],
            'level': 'DEBUG',
        },
        'basic.error': {
            'handlers': ['basic_e'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
    'handlers': {
        'basic_h': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs/debug.log'),
            'formatter': 'simple',
        },
        'basic_e': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs/error.log'),
            'formatter': 'simple',
        },
    },
    'formatters': {
        'simple': {
            'format': '{levelname} : {asctime} : {message}',
            'style': '{',
        }
    }
}


PASSWORD_RESET_TIMEOUT = 600


# Emails settings
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = config('EMAIL_HOST', default='localhost')
EMAIL_PORT = config('EMAIL_PORT', default=25, cast=int)
EMAIL_USE_SSL = config('EMAIL_USE_SSL', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='no-reply@trip.dev')


PAYSTACK_SECRET = config('PAYSTACK_SECRET', default='')

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=200),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
}

MAX_STORE_IMAGE = 6

ALLOWED_IMAGE_EXTS = ['jpeg', 'jpg', 'png']

PRINT_LOG = True
OFF_EMAIL = True


VEHICLE_SPECIFICATION_DEFAULT = False


MAX_IMAGE_UPLOAD_SIZE = 2621440  # 2.5MB


# Transport settings
MAX_TRIP_PLANS_DAYS = 30
EVERYDAY = 'everyday'
SEARCH_TRIPS_CACHE_TIME_IN_SECONDS = 180


LOGIN_URL = 'admin:login'

STATUS_SET = {
    # Success codes (2)
    '200': 'Request is successful',
    '201': 'Successfully created',

    # Error codes (4)
    '400': 'Error processing your request',
    '403': "You do not have permission to access this resource.",
    '404': 'Requested resource does not exist',
    '424': 'User does not exist.',
    '425': 'Token passed is not valid.',
    '426': 'User has already been verified.',
    '427': 'uidb64 value passed is not valid.',
    '428': 'ID value was not passed with the request.',
    '429': 'Email value was not passed with the request.',
    '431': 'User email is not yet verified',
    '432': 'Account has been deactivated',
    '433': 'Invalid authorization code signature',
    '434': 'No logistics are available to move package from pickup\
to delivery destination',
    '435': 'Package transaction already in process or processed',
}


FLW_TITLE = "Trip Value"
FLW_LOGO = "https://tripvalue.com/static/images/logo.png"
FLW_DESCRIPTION = "Trip Value is a platform that allows you to\
send packages to your loved ones in Nigeria from anywhere in the world."
FLW_SECRET_KEY = config('FLW_SECRET_KEY', default='')
