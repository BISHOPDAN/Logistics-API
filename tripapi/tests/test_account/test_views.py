from typing import TypeVar
import pytest

from account.models import User
from django.test.client import Client
from rest_framework import status
from rest_framework.reverse import reverse
# from utils.base.general import url_with_params

T = TypeVar('T', bound=Client)


pytestmark = pytest.mark.django_db


def login_user(admin_api_key_headers, client: T):
    url = reverse('auth:login')
    data = {
        'email': 'test_email@gmail.com',
        'password': 'randopass'
    }
    response = client.post(
        url, data, format='json',
        **admin_api_key_headers)

    return response.data.get('tokens', '')


@pytest.mark.usefixtures('basic_user', 'admin_user')
def test_user_count():
    user_count = User.objects.count()
    assert user_count == 2


def test_user_login_api_permissions(client: T):
    url = reverse('auth:login')
    data = {}
    response = client.post(
        url, data, format='json')
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.usefixtures('basic_user')
def test_user_login(client: T, admin_api_key_headers, basic_user_data):
    url = reverse('auth:login')
    response = client.post(
        url, basic_user_data, format='json',
        **admin_api_key_headers
    )
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()['data']
    tokens = response_data['tokens']
    user = response_data['user']
    assert bool(tokens) is True
    assert bool(user) is True
    assert bool(tokens['refresh']) is True
    assert bool(tokens['access']) is True


@pytest.mark.usefixtures('basic_user')
def test_user_login_unverified_email(
    client: T, admin_api_key_headers, basic_user_data, basic_user
):
    basic_user.verified_email = False
    basic_user.save()
    url = reverse('auth:login')
    response = client.post(
        url, basic_user_data, format='json',
        **admin_api_key_headers
    )
    assert response.status_code == 431
    response_data = response.json()['data']
    tokens = response_data['tokens']
    email = response_data['email']
    assert email == 'test_email@gmail.com'
    assert bool(tokens) is True
    assert bool(tokens['uidb64']) is True
    assert bool(tokens['token']) is True


def test_user_registration_permission(client: T):
    url = reverse('auth:register')
    response = client.post(url, format='json')
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.parametrize(
    'name, value',
    [
        ('email', 'sketcherslodge'),
        ('first_name', 'Netrobe000000000000000000000000'),
        ('last_name', 'webby;d8$'),
        ('password', '1234'),
    ]
)
def test_user_registration_wrong_data(
    client: T, user_create_data: dict, admin_api_key_headers,
    name, value
):
    url = reverse('auth:register')
    user_create_data[name] = value
    response = client.post(
        url, user_create_data, format='json', **admin_api_key_headers)
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_user_registration_success(
    client: T, user_create_data: dict, admin_api_key_headers
):
    url = reverse('auth:register')
    response = client.post(
        url, user_create_data, format='json', **admin_api_key_headers)
    assert response.status_code == status.HTTP_201_CREATED
    response_data = response.json()['data']
    tokens = response_data['tokens']
    user = response_data['user']
    assert bool(user) is True
    assert bool(tokens) is True
    assert bool(tokens['uidb64']) is True
    assert bool(tokens['token']) is True

    # def test_change_password(self):
    #     """
    #     Test to change user password with wrong data
    #     (with and without api key)
    #     and correct data with api key
    #     """
    #     # Get access token with login user
    #     token = login_user()['access']
    #     url = reverse('auth:change_password')
    #     client.credentials(HTTP_AUTHORIZATION='Bearer '+token)
    #     data = {
    #         'old_password': 'wrongpass',
    #         'new_password': 'randopass',
    #         'confirm_password': 'randopass'
    #     }
    #     # Wrong data without api key
    #     response = client.put(url, data, format='json')
    #     assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    #     # Wrong data with api key
    #     response = make_post(url, data)
    #     assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    #     data = {
    #         'old_password': 'randopass',
    #         'new_password': 'newpass12',
    #         'confirm_password': 'newpass12'
    #     }
    #     # Correct data with api key
    #     response = make_post(url, data)
    #     assertEqual(response.status_code, status.HTTP_200_OK)

    # def test_otp_generator(self):
    #     """
    #     Test otp generator with and without api key
    #     """
    #     url = reverse('auth:gen_otp')

    #     # Without api key
    #     response = client.get(url, format='json')
    #     assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    #     # With api key
    #     response = client.get(url, **get_headers())
    #     assertEqual(response.status_code, status.HTTP_200_OK)

    # def test_email_token(self):
    #     """
    #     1. Test email token generation and validation
    #     with and without api key,
    #     test for wrong user id,
    #     We will be using this utility function <url_with_params> to get links
    #     like this <www.google.com/?id=1>
    #     (SO it takes the url and data dict to
    #     return <www.google.com/?id=1>)

    #     2. We will also use the response of
    #     the correct request to test validate
    #     token url view. Test for wrong and right values
    #     """
    #     # 1: Generate token view test
    #     url = reverse('auth:gen_token')
    #     data = {
    #         'id': ''
    #     }

    #     # Without api key
    #     response = client.get(url_with_params(url, data), format='json')
    #     assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    #     # With api key
    #     response = client.get(
    #         url_with_params(url, data), format='json', **get_headers())
    #     assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    #     # With api key and correct data
    #     data = {
    #         'id': 1
    #     }
    #     correct_response = client.get(
    #         url_with_params(url, data), format='json', **get_headers())
    #     assertEqual(correct_response.status_code, status.HTTP_200_OK)

    #     # 2: Validate email token view test
    #     url = reverse('auth:validate_token')

    #     # a. With wrong data and no api key
    #     response = client.post(url, format='json')
    #     assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    #     # b. With wrong data and api key
    #     response = client.get(url, format='json', **get_headers())
    #     assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    #     # c. Get the uid and token from the correct_response
    #     uidb64 = correct_response.data.get('uidb64', '')
    #     token = correct_response.data.get('token', '')
    #     data = {
    #         'uidb64': uidb64,
    #         'token': token,
    #     }

    #     response = make_post(url, data)
    #     assertEqual(response.status_code, status.HTTP_200_OK)

    # def test_refresh_token(self):
    #     """
    #     Test to check the functionality of token refresh
    #     """
    #     # Get tokens with login user
    #     tokens = login_user()
    #     refresh = tokens['refresh']

    #     url = reverse('auth:token_refresh')
    #     data = {
    #         'refresh': 'wrongpass'
    #     }

    #     # Wrong data without api key
    #     response = client.post(url, data, format='json')
    #     assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    #     # Wrong data with api key
    #     response = make_post(url, data)
    #     assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    #     data = {
    #         'refresh': refresh
    #     }
    #     # Correct data with api key
    #     response = make_post(url, data)
    #     assertEqual(response.status_code, status.HTTP_200_OK)

    # def test_forget_password(self):
    #     """
    #     Test for forget user password with wrong
    #     data (with and without api key)
    #     and correct data with api key
    #     """
    #     url = reverse('auth:forget_password')
    #     correct_data = {
    #         'id': 1,
    #         'new_password': 'randopass',
    #         'confirm_password': 'randopass'
    #     }
    #     # Without api key
    #     response = client.put(url, format='json')
    #     assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    #     # Wrong data with api key
    #     clone_data = correct_data.copy()
    #     clone_data['id'] = ''
    #     response = client.patch(
    #         url, clone_data, format='json', **get_headers())
    #     assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    #     # Wrong data with api key
    #     wrong_data = {
    #         'new_password': 'pass1234',
    #         'confirm_password': 'pass1234'
    #     }
    #     for key, value in wrong_data.items():
    #         # Check similar code in registration test for comments
    #         data = correct_data.copy()
    #         data[key] = value
    #         response = client.patch(
    #             url, data, format='json', **get_headers())
    #         assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    #     # Correct data with api key
    #     response = client.patch(
    #         url, correct_data, format='json', **get_headers())
    #     assertEqual(response.status_code, status.HTTP_200_OK)

    # def test_user_info(self):
    #     """
    #     Test for user information urls
    #     (list/retrive) with and without api key
    #     """
    #     # 1. User list view api test
    #     url = reverse('auth:user_list')

    #     # Without api key
    #     response = client.get(url, format='json')
    #     assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    #     # With api key
    #     response = client.get(url, format='json', **get_headers())
    #     assertEqual(response.status_code, status.HTTP_200_OK)

    #     # 2. User Detail api test
    #     url = reverse('auth:user_data', kwargs={'id': 1})
    #     err_url = reverse('auth:user_data', kwargs={'id': 0})

    #     # a. Wrong data without api key
    #     response = client.get(url, format='json')
    #     assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    #     # b. Wrong data with api key
    #     response = client.get(
    #         err_url, format='json', **get_headers())
    #     assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    #     # c. correct data with api key
    #     response = client.get(url, format='json', **get_headers())
    #     assertEqual(response.status_code, status.HTTP_200_OK)

    # def test_sendmail(self):
    #     """
    #     Test for sending mail to user with and without api key
    #     """
    #     url = reverse('auth:send_mail')

    #     # Without api key
    #     response = client.post(url, format='json')
    #     assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    #     # With api key (correct data)
    #     data = {
    #         'email': 'demo@gmail.com',
    #         'subject': 'Testing api',
    #         'message': 'Your message test'
    #     }
    #     response = client.post(
    #         url, data, format='json', **get_headers())
    #     assertEqual(response.status_code, status.HTTP_200_OK)
