from .testmode import *  # noqa

ALLOWED_HOSTS = ['api.tripvalue.com.ng']


SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=5)  # noqa
}
