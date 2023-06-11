"""
Utilities for projects
"""

import datetime
import os
import socket
import sys
from contextlib import contextmanager
from functools import reduce
from io import StringIO
from pathlib import Path
from typing import Callable, Generator, Iterable, List, Tuple
from uuid import uuid4

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.mail import send_mail
from django.db.models.query import QuerySet
from django.http.response import JsonResponse
from django.utils.crypto import get_random_string
from rest_framework_simplejwt.tokens import RefreshToken

from .constants import WEEKDAYS
from .logger import err_logger, logger  # noqa


def get_day_value(day: str):
    return WEEKDAYS[day]


def get_model_fields(model):
    return [field.name for field in model._meta.fields]


class Crypthex:
    """
    Class for encryption and decryption
    """

    def __init__(self):
        self.key = settings.ENCRYPTING_KEY

        # Instance the Fernet class with the key
        self.fernet = Fernet(self.key.encode())

    def encrypt(self, text):
        """
        Use the fernet created in the __init__ to encrypt text,
        which will return an encoded string example
        of result = b'example'
        """
        text = str(text)

        result = self.fernet.encrypt(text.encode())
        return result.decode()

    def decrypt(self, text):
        """
        Use the fernet created in the __init__ to decrypt text,
        which will return an encoded string
        example of result = b'example'
        """
        text = str(text)
        try:
            result = self.fernet.decrypt(text.encode())
            return result.decode()
        except InvalidToken:
            pass

        return False


cryptor = Crypthex()


def random_otp():
    """
    Generating OTP with 6 digits
    """
    return get_random_string(length=6, allowed_chars='1234567890')


def invalid_str(value):
    """
    To validate model data like charfield
    """
    for i in '@#$%^&*+=://;?><}{[]()':
        if i in value:
            return True
    return False


def convert_bytes_to_mb(num):
    """Convert bytes to megabyte"""
    return num / 1024 / 1024


def choices_to_dict(list_tup: Iterable[Tuple[str, str]]):
    """
    Converts model choices to dictionary format
    like
    [
        {
            'name': ...,
            'value': ...
        }
    ]
    """
    return [{'value': a[0], 'name': a[1]} for a in list_tup]


def printt(*args, **kwargs):
    """
    Override python print to only print when allowed
    """
    if settings.PRINT_LOG is True:
        return print(*args, **kwargs)


def send_email(email, subject, message, fail=True):
    """
    Send mail function
    """
    if settings.DEBUG is True:
        print(message)

    if settings.OFF_EMAIL:
        return True

    val = send_mail(
        subject=subject, message=message,
        html_message=message, from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email], fail_silently=fail)

    return True if val else False


def remove_session(request, name):
    """
    Remove sessions from request
    """
    session = request.session.get(name, None)
    if session is not None:
        del request.session[name]


def tup_to_dict(tup: tuple) -> dict:
    """
    Convert model choices (tuples) to dictionary
    """
    jsonObj = []

    for key, value in tup:
        obj = dict()
        obj['key'] = key
        obj['value'] = value
        jsonObj.append(obj)

    return jsonObj


def verify_ip(ip):
    """
    Verify that ip is valid
    """
    try:
        socket.inet_aton(ip)
        return True
    except socket.error:
        pass
    return False


def get_client_ip(request):
    """
    Get ip address from request obj
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')

    if verify_ip(ip):
        return ip


def verify_next_link(next):
    """
    Validates the next value
    """
    if next:
        if next.startswith('/'):
            return next


def get_next_link(request):
    """
    Get the next link from the url
    """
    next = request.GET.get('next')
    return verify_next_link(next)


def deslug(text):
    """
    Convert string from snake casing to normal
    """
    texts = text.split('_')
    texts = [i.capitalize() for i in texts]
    return ' '.join(texts)


def add_queryset(a, b) -> QuerySet:
    """
    Add two querysets
    """
    return a | b


def merge_querysets(*args) -> QuerySet:
    """
    Merge querysets
    """
    return reduce(add_queryset, args)


def create_unique_tracking_id(prefix='TV'):
    """
    Generates a random string with prifix
    """
    return f"{prefix}-" + str(uuid4())


def get_name_from_email(name: str):
    """
    Get name from email and generate unique username
    """
    return name + "_" + get_random_string(
        length=5, allowed_chars='1234567890'
    )


def get_tokens_for_user(user):
    """
    Get the tokens for user
    """
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


def url_with_params(url, params):
    """
    Url is a relative or full link,
    params is a dictionary of key/value pairs of the query parameters
    {id: 3, name: 'John doe'}
    """
    # Add trailing backslash to url
    if not url.endswith('/'):
        url += '/'

    # Join the key/value pairs into a string
    assiged = [f'{key}={value}' for key, value in params.items()]

    return url + '?' + '&'.join(assiged)


error_sets = {
    'ObjectNotFound': {
        'status': 404,
        'types': {
            'user-001': {
                'message': 'User does not exist.'
            }
        }
    },
    'TokenValidationError': {
        'status': 400,
        'types': {
            'user-001': {
                'message': 'Token passed is not valid.'
            },
            'user-002': {
                'message': 'User has already been verified.'
            },
            'user-003': {
                'message': 'Uidb64 value passed is not valid.'
            }
        }
    },
    'RequestError': {
        'status': 400,
        'types': {
            'req-001': {
                'message': 'ID value was not passed with the request.'
            },
            'req-002': {
                'message': 'Email value was not passed with the request.'
            },
            'req-003': {
                'message': 'This user has no business connected',
            }
        }
    },
}


class CustomError:
    def __init__(
        self, status='', type='',
        code='', message='', request=None
    ):
        self.type = type
        self.code = code
        self.status = status
        self.message = message
        self.path = ''

        if request is not None:
            self.path = request.META['PATH_INFO']

        # Get the error obj
        if type:
            obj = error_sets.get(type)

            if obj and code:
                main_err = obj['types'].get(code)
                self.status = obj.get('status', '')

                if main_err:
                    self.message = main_err.get('message', '')

                    main_status = main_err.get('status', '')
                    if main_status:
                        self.status = main_status

        if status:
            self.status = status

    def response(self):
        dict_form = {
            "status": self.status,
            "error": self.type,
            "code": self.code,
            "message": self.message,
            "path": self.path
        }

        return JsonResponse(data=dict_form, status=self.status)


# Class for customizing rest api return response
class DecorResponse:
    def __init__(
        self, request=None, success='',
        status='200', message='', data=None
    ):
        # Convert status to string
        status = str(status)

        # Initialize object properties
        self.status = status
        self.message = message
        self.data = data
        self.path = ''

        # Success defaults to false if not passed
        self.success = success if success else False

        # Set the success status to true if it is a status code that starts with '2' # noqa
        if status.startswith('2'):
            self.success = True

        # Get the url path
        if request is not None:
            self.path = request.META['PATH_INFO']

        # Get the status set obj
        if not message:
            self.message = settings.STATUS_SET.get(status, '')

    def response(self):
        """
        Return data in format
        data = {
            'status',
            'success',
            'message',
            'data',
            'path',
        }
        """

        dict_form = {
            "success": self.success,
            "status": self.status,
            "message": self.message,
            "data": self.data,
            "path": self.path,
        }

        return dict_form


def vehicle_upload_path(instance, filename):
    """
    Function to get the base path of a vehicle in the format
    transporters/<transporter_name>/vehicles/<vehicle_folder_name>
    """
    transporter = instance.transporter.slug_name

    # Get vehicle tag
    vehicle_folder_name = str(instance.tag)

    return os.path.join(
        "transporters",
        transporter,
        "vehicles",
        vehicle_folder_name,
        filename)


def driver_upload_path(instance, folder_name):
    """
    Function to get the base path of a driver image
    in the format 
    transporters/<transporter_name>/drivers/<driver_folder_name>/<folder_name>
    """  # noqa

    transporter = instance.transporter.slug_name

    # Get driver folder name like driver_<user_profle_name>
    driver_folder_name = "driver_" + instance.user.profile.get_user_name_with_id()  # noqa

    return os.path.join(
        "transporters",
        transporter,
        "drivers",
        driver_folder_name,
        folder_name)


def driver_upload_path_licence(instance, filename):
    """
    Get driver folder path with folder name licence
    """
    base_path = driver_upload_path(instance, 'licence')
    return Path(base_path) / filename


def driver_upload_path_idcard(instance, filename):
    """
    Get driver folder path with folder name id-card
    """
    base_path = driver_upload_path(instance, 'id-card')
    return Path(base_path) / filename


def is_exc_obj_does_not_exist(e: Exception):
    return e.__class__.__name__\
        == 'RelatedObjectDoesNotExist'


def check_raise_exc(e: Exception):
    """
    Raise exception if not RelatedObjectDoesNotExist

    :param e: Supplied exception class
    :type e: Exception
    :raises e: Raise exception passed to it
    """

    if not is_exc_obj_does_not_exist(e):
        raise e


def split_datetime(datetime) -> List[str]:
    """
    Split passed datetime into date and time

    :return: YYYY-mm-dd and H:M:S
    :rtype: List[str]
    """
    date, time = str(datetime).split()
    time = time.split('.')[0]
    return date, time


def regexify(name: str) -> str:
    """Wraps name with regex to use in restframework action url path"""
    return f"(?P<{name}>[^/.]+)"


def today():
    """Return today's date only"""
    return datetime.date.today()


@contextmanager
def capture_output(func: Callable[..., None]) -> Generator[str, None, None]:
    """Context manager to capture
    standart output when calling function as
    a string"""
    old_stdout = sys.stdout
    sys.stdout = mystdout = StringIO()
    func()
    sys.stdout = old_stdout

    yield mystdout.getvalue()
