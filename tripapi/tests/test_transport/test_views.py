import datetime
from typing import Type

import pytest
from account.models import User
from project_api_key.models import ProjectApiKey
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase
from transport.models import Driver, Transporter
from utils.base.constants import TOMORROW

from utils.base._types import _R


class UtilityMethods(APITestCase):
    test_password = 'randopass'
    basic_user_email = 'basic@gmail.com'
    staff_email = 'staff@gmail.com'
    transporter_email = 'transporter@gmail.com'
    driver_email = 'driver@gmail.com'
    test_dy_email = "user@example.com"

    def create_user(self, email: str, is_staff: bool = False) -> Type[User]:
        """
        Reduce create user codes,
        by implementing User.create_user in a
        single function
        """
        user = User(email=email)
        user.active = True
        user.admin = False
        user.staff = is_staff
        user.verified_email = True
        user.set_password(self.test_password)
        user.save()
        return user

    def create_basic_user(self):
        """
        Create a basic user that is neither
        a transporter or a staff with api keys
        """
        self.create_user(self.basic_user_email)

    def create_staff(self):
        """
        Create a Staff user with API keys
        """
        admin = self.create_user(self.staff_email, True)

        # Generate staff api key
        project_api_key = ProjectApiKey.objects.create(user=admin)
        key = project_api_key.demo_sec
        project_api_key.demo_sec = ''
        project_api_key.save()

        # Globalize key
        self.sec_key = key
        self.pub_key = project_api_key.pub_key

    def create_transporter(self) -> Type[Transporter]:
        """
        Create a transporter user
        """
        user = self.create_user(self.transporter_email)
        return Transporter.objects.create(
            user=user,
            name='Django Test Transporter'
        )

    def get_headers(self) -> dict:
        return {
            'HTTP_BEARER_API_KEY': self.pub_key,
            'HTTP_BEARER_SEC_API_KEY': self.sec_key,
        }

    def make_post(self, url: str, data: dict = None):
        return self.client.post(
            url, data, format='json',
            **self.get_headers())

    def make_get(self, url: str):
        return self.client.get(
            url, format='json', **self.get_headers())

    def make_put(self, url: str, data: dict = None):
        return self.client.put(
            url, data, format='json',
            **self.get_headers())

    def make_patch(self, url: str, data: dict = None):
        return self.client.patch(
            url, data, format='json',
            **self.get_headers())

    def login_user(self, email):
        url = reverse('auth:login')
        data = {
            'email': email,
            'password': self.test_password
        }
        response = self.make_post(url, data)
        tokens = response.data.get('tokens', '')
        token = tokens['access']
        self.client.credentials(HTTP_AUTHORIZATION='Bearer '+token)

    def login_transporter(self):
        self.login_user(self.transporter_email)

    def login_basic_user(self):
        self.login_user(self.basic_user_email)

    def create_driver(self) -> Type[Driver]:
        """
        Create a normal user that's also driver

        :return: Newly created driver
        :rtype: Type[Driver]
        """

        user = self.create_user(self.driver_email)
        driver = Driver.objects.create(
            user=user,
            transporter=self.transporter
        )
        return driver


class TransportDriverAPITest(UtilityMethods):
    def setUp(self):
        self.transporter = self.create_transporter()
        self.create_staff()
        self.create_basic_user()

    def test_driver_create(self):
        '''
        Test successfull creation of new drivers
        '''
        url = reverse('transport:driver-create')
        data = {
            "first_name": "user",
            "last_name": "example",
            "email": self.test_dy_email,
            "phone": "+9999999999",
            "address": "full user address",
            "send_mail_verification": True
        }
        self.login_transporter()
        response = self.make_post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        computed = response.data.get('first_name')
        self.assertEqual(computed, 'user')
        computed = response.data.get('last_name')
        self.assertEqual(computed, 'example')
        computed = response.data.get('email')
        self.assertEqual(computed, self.test_dy_email)

    def test_driver_email_validation(self):
        '''
        Test successfull email validation of new drivers
        '''
        url = reverse('transport:driver-create')
        data = {
            "first_name": "user",
            "last_name": "example",
            "email": self.transporter_email,
            "phone": "+9999999999",
            "address": "full user address",
            "send_mail_verification": False
        }
        self.login_transporter()
        response = self.make_post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_driver_update_patch(self):
        driver = self.create_driver()
        url = reverse('transport:driver-update', args=[driver.tracking_code])
        new_name = "new_name"
        data = {
            "first_name": new_name
        }
        self.login_transporter()
        response = self.make_patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        computed_name = response.data.get('first_name')
        self.assertEqual(computed_name, new_name)

    def test_driver_update_patch_email_validation(self):
        driver = self.create_driver()
        url = reverse('transport:driver-update', args=[driver.tracking_code])
        data = {
            "email": 'test@gmail.com'
        }
        self.login_transporter()
        response = self.make_patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_driver_update(self):
        '''
        Test successfull update driver
        '''
        driver = self.create_driver()
        url = reverse('transport:driver-update', args=[driver.tracking_code])
        data = {
            "first_name": "user",
            "last_name": "example",
            "phone": "+9999999999",
            "address": "full user address",
            "send_mail_verification": False
        }
        self.login_transporter()
        response = self.make_put(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        for attr, value in data.items():
            computed = response.data.get(attr)
            self.assertEqual(computed, value)

    def test_driver_detail(self):
        '''
        Test successfull update driver
        '''
        driver = self.create_driver()
        url = reverse('transport:driver-detail', args=[driver.tracking_code])
        self.login_transporter()
        response = self.make_get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        computed = response.data.get('email')
        self.assertEqual(computed, driver.user.email)

        data = ['first_name', "last_name", "phone", "address"]
        for attr in data:
            value = getattr(driver.user.profile, attr)
            computed = response.data.get(attr)
            self.assertEqual(computed, value)

        data = ["licence", "id_card", "send_mail_verification"]
        for attr in data:
            value = getattr(driver, attr)
            computed = response.data.get(attr)
            self.assertEqual(computed, value)


@pytest.mark.django_db
class TestTripTemplateViewSetAPI():
    def test_tripplaning_create(
        self, driver, vehicle,
        transporter_post
    ):
        url = reverse('transport:tripplaning-create')
        data = {
            'trip_type': 'intracity',
            'driver': driver.pk,
            'vehicle': vehicle.pk,
            'origin': 'Lagos',
            'destination': 'Ibadan',
            'boarding_point': 'Ojota',
            'alighting_point': 'Iwo Road',
            'take_off_time': datetime.time(4, 4, 4),
            'duration': datetime.timedelta(hours=5),
            'amount': 5000,
            'start_date': datetime.date.today(),
            'recurring': 'saturday',
            'pre_booked_seats': 4,
        }
        response = transporter_post(url, data)
        assert response.status_code == status.HTTP_201_CREATED

    def test_tripplaning_list(
        self, base_trip_plan,
        transporter_get
    ):
        url = reverse('transport:tripplaning-list')
        base_trip_plan.save()
        response = transporter_get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_tripplaning_detail(
        self, base_trip_plan,
        transporter_get
    ):
        base_trip_plan.save()
        url = reverse(
            'transport:tripplaning-detail',
            args=[base_trip_plan.tracking_code]
        )
        response = transporter_get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_tripplaning_put(
        self, base_trip_plan,
        transporter_put, driver, vehicle
    ):
        base_trip_plan.save()
        url = reverse(
            'transport:tripplaning-update',
            args=[base_trip_plan.tracking_code]
        )
        data = {
            'trip_type': 'intracity',
            'driver': driver.pk,
            'vehicle': vehicle.pk,
            'origin': 'NewOrigin',
            'destination': 'Ibadan',
            'boarding_point': 'Ojota',
            'alighting_point': 'Iwo Road',
            'take_off_time': datetime.time(4, 4, 4),
            'duration': datetime.timedelta(hours=5),
            'amount': 5000,
            'start_date': datetime.date.today(),
            'recurring': 'saturday',
            'pre_booked_seats': 4,
        }
        response = transporter_put(url, data)
        assert response.status_code == status.HTTP_200_OK
        assert response.data.get('origin') == 'NewOrigin'

    def test_tripplaning_patch(
        self, base_trip_plan,
        transporter_patch
    ):
        base_trip_plan.save()
        url = reverse(
            'transport:tripplaning-update',
            args=[base_trip_plan.tracking_code]
        )
        data = {
            'pre_booked_seats': 10,
        }
        response = transporter_patch(url, data)
        assert response.status_code == status.HTTP_200_OK
        assert response.data.get('pre_booked_seats') == 10

    def test_tripplaning_delete(
        self, base_trip_plan,
        transporter_delete
    ):
        base_trip_plan.save()
        url = reverse(
            'transport:tripplaning-delete',
            args=[base_trip_plan.tracking_code]
        )
        response = transporter_delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.django_db
class TestTripObjectAPI():
    @pytest.mark.usefixtures('trip_plan')
    def test_trip_list(self, transporter_get):
        url = reverse('transport:trip-list')
        response = transporter_get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_trip_all(self, get, baked_trips):
        url = reverse('transport:trip-all')
        response: _R = get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["data"]['count'] == len(baked_trips)

    @pytest.mark.usefixtures('trip_plan')
    def test_trip_started(self, transporter_get):
        url = reverse('transport:trip-started')
        response: _R = transporter_get(url)
        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.usefixtures('trip_plan')
    def test_trip_pending(self, transporter_get):
        url = reverse('transport:trip-pending')
        response = transporter_get(url)
        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.usefixtures('trip_plan')
    def test_trip_completed(self, transporter_get):
        url = reverse('transport:trip-completed')
        response = transporter_get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_trip_search_authorize(self, keyless_get):
        url = reverse('transport:trip-search')
        response = keyless_get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_trip_search_required_parameters(self, get):
        params = {
            "origin": "",
            "destination": "",
            "passengers": "1",
            "leave_date": "",
            "return_date": "fake_param",
        }
        url = reverse('transport:trip-search')
        response = get(url, params)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json().get("data") == "Invalid query parameter"

    def test_trip_search_required_parameters_fail(self, get):
        url = reverse('transport:trip-search')
        response = get(url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json().get("data").startswith(
            "Missing required query parameter origin")

    @pytest.mark.usefixtures("create_search_trips")
    def test_trip_search(self, get):
        params = {
            "origin": "Lagos, ojota",
            "destination": "Ibadan",
            "passengers": 1,
            "leave_date": TOMORROW,
        }
        url = reverse('transport:trip-search')
        response = get(url, params)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["data"]['count'] == 2

    @pytest.mark.usefixtures('trip_plan')
    def test_trip_cancelled(self, transporter_get):
        url = reverse('transport:trip-cancelled')
        response = transporter_get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_tripplaning_detail(
        self, trip,
        transporter_get
    ):
        url = reverse(
            'transport:trip-detail',
            args=[trip.tracking_code]
        )
        response = transporter_get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_trip_put(
        self, trip,
        transporter_put, driver, vehicle
    ):
        url = reverse(
            'transport:trip-update',
            args=[trip.tracking_code]
        )
        data = {
            'trip_type': 'intracity',
            'driver': driver.pk,
            'vehicle': vehicle.pk,
            'origin': 'NewOrigin',
            'destination': 'Ibadan',
            'boarding_point': 'Ojota',
            'alighting_point': 'Iwo Road',
            'take_off_time': datetime.time(4, 4, 4),
            'duration': datetime.timedelta(hours=5),
            'amount': 5000,
            'leave_date': datetime.date.today(),
        }
        response = transporter_put(url, data)
        assert response.status_code == status.HTTP_200_OK
        assert response.data.get('origin') == 'NewOrigin'

    def test_trip_patch(
        self, trip,
        transporter_patch
    ):
        url = reverse(
            'transport:trip-update',
            args=[trip.tracking_code]
        )
        data = {
            'amount': 10000,
        }
        response = transporter_patch(url, data)
        assert response.status_code == status.HTTP_200_OK
        assert response.data.get('amount') == 10000

    def test_trip_delete(
        self, trip,
        transporter_delete
    ):
        url = reverse(
            'transport:trip-delete',
            args=[trip.tracking_code]
        )
        response = transporter_delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
