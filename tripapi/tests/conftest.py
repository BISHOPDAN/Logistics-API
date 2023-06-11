from functools import partial
from typing import Callable, Dict, TypeVar
from unittest import TestCase

import pytest
from rest_framework.test import APIClient

from account.models import User
from project_api_key.models import ProjectApiKey
from transport.models import Transporter
from utils.base.general import get_tokens_for_user
from utils.base.fields import TrackingCodeField
from model_bakery import baker


U = TypeVar('U', bound=TestCase)


transporter_email = 'transporter@gmail.com'
basic_email = 'test_email@gmail.com'

drf_client = APIClient()

API_CLIENT_METHODS: Dict[str, Callable[..., None]] = {
    'post': drf_client.post,
    'patch': drf_client.patch,
    'put': drf_client.put,
    'delete': drf_client.delete,
    'get': drf_client.get,
}


@pytest.fixture(autouse=True)
def register_baker_fields():
    TrackingCodeField.register(baker)


@pytest.fixture
def test_case():
    return TestCase()


@pytest.fixture
def basic_user_data():
    data = {
        'email': basic_email,
        'password': 'randopass',
    }
    return data


@pytest.fixture
def keyless_base_client():

    def inner(method: str = "post"):

        method = method if method is not None else "post"
        client = API_CLIENT_METHODS[method]

        def child(url: str, data: dict = None, headers: dict = None):
            if headers is None:
                headers = {}

            return client(
                url, data, format='json',
                **headers
            )

        return child

    return inner


@pytest.fixture
def keyless_post(keyless_base_client):
    return keyless_base_client()


@pytest.fixture
def keyless_get(keyless_base_client):
    return keyless_base_client('get')


@pytest.fixture
def keyless_delete(keyless_base_client):
    return keyless_base_client('delete')


@pytest.fixture
def keyless_patch(keyless_base_client):
    return keyless_base_client('patch')


@pytest.fixture
def keyless_put(keyless_base_client):
    return keyless_base_client('put')


@pytest.fixture
def base_client(admin_api_key_headers, keyless_base_client):

    def inner(method=None):

        def child(url: str, data: dict = None, headers: dict = None):

            if headers is None:
                headers = {}

            headers.update(admin_api_key_headers)

            return keyless_base_client(method)(url, data, headers)

        return child

    return inner


@pytest.fixture
def post(base_client):
    return base_client()


@pytest.fixture
def get(base_client):
    return base_client('get')


@pytest.fixture
def delete(base_client):
    return base_client('delete')


@pytest.fixture
def patch(base_client):
    return base_client('patch')


@pytest.fixture
def put(base_client):
    return base_client('put')


@pytest.fixture
def transporter_post(transporter_headers, post):
    return partial(post, headers=transporter_headers)


@pytest.fixture
def transporter_get(transporter_headers, get):
    return partial(get, headers=transporter_headers)


@pytest.fixture
def transporter_put(transporter_headers, put):
    return partial(put, headers=transporter_headers)


@pytest.fixture
def transporter_patch(transporter_headers, patch):
    return partial(patch, headers=transporter_headers)


@pytest.fixture
def transporter_delete(transporter_headers, delete):
    return partial(delete, headers=transporter_headers)


@pytest.fixture
def transporter_headers(transporter):
    token = get_tokens_for_user(transporter.user).get('access')
    return {
        'HTTP_AUTHORIZATION': f'Bearer {token}'
    }


@pytest.fixture
def user_create_data():
    correct_data = {
        'email': 'sketcherslodge@email.com',
        'first_name': 'Netrobe',
        'last_name': 'webby',
        'password': 'newpass12',
    }
    return correct_data


@pytest.fixture
def basic_user(basic_user_data):
    user = User.objects.create_user(**basic_user_data)
    user.verified_email = True
    user.save()
    user.profile.first_name = "test"
    user.profile.last_name = "user"
    user.profile.save()
    return user


@pytest.fixture
def admin_user():
    admin = User.objects.create_superuser(
        email='admin@gmail.com',
        password='randopass'
    )
    admin.verified_email = True
    admin.save()
    return admin


@pytest.fixture
def admin_api_key_headers(admin_user):
    project_api_key = ProjectApiKey.objects.create(user=admin_user)
    key = project_api_key.demo_sec
    project_api_key.demo_sec = ''
    project_api_key.save()

    sec_key = key
    pub_key = project_api_key.pub_key
    return {
        'HTTP_BEARER_API_KEY': pub_key,
        'HTTP_BEARER_SEC_API_KEY': sec_key,
    }


@pytest.fixture
def transporter(basic_user):
    basic_user.pk = None
    basic_user.email = transporter_email
    basic_user.save()
    user = User.objects.get(pk=basic_user.pk)
    return Transporter.objects.create(
        user=user,
        name='Django Test Transporter'
    )


@pytest.fixture
def dummy_request():
    class Request:
        user = None
    return Request()


@pytest.fixture(autouse=True)
def use_dummy_media_path(settings, tmp_path):
    settings.MEDIA_ROOT = settings.BASE_DIR / tmp_path
