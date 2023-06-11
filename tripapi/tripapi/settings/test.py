# flake8: noqa

from .dev import *

SECRET_KEY = "fake-key"

INSTALLED_APPS += [
    "tests"
]


# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     },
# }

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': "trip_testing_fake_db",
        'USER': config("TEST_DB_USER"),
        'PASSWORD': config("TEST_DB_PASSWORD"),
        'HOST': 'localhost',
        'PORT': '',
    }
}

DB_DEFAULT = "postgres"

# use default loc mem cache for tests
CACHES['default']["BACKEND"] = 'django.core.cache.backends.locmem.LocMemCache'
