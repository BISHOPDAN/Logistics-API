import datetime
from typing import TypeVar
from unittest import TestCase

import pytest
from rest_framework.serializers import ValidationError
from transport.api.base import serializers
from transport.validators import ErrCode
from utils.base.constants import unit  # noqa

from tests.conftest import transporter_email, basic_email


U = TypeVar('U', bound=TestCase)


def test_trans_base_serializer():
    data = {
        'bookings_unconfirmed': 1,
        'trips_pending': 1,
        'bookings_cancelled': 1,
    }
    serial = serializers.TransBaseSerializer(data=data)
    serial.is_valid(raise_exception=True)


def test_vehicle_list_type():
    data = {
        'name': 'test',
        'value': 'value',
    }
    serial = serializers.ChoiceOptionSerializer(data=data)
    serial.is_valid(raise_exception=True)


def test_vehicle_list_types():
    data = {
        'name': 'test',
        'value': 'value',
    }
    values = {'types': [data]}
    serials = serializers.ChoiceSerializer(data=values)
    serials.is_valid(raise_exception=True)


@pytest.mark.django_db
class TestTransporterSerializer():
    serializer_class = serializers.TransporterSerializer

    def test_transporter_create(self, test_case: U, dummy_request, basic_user):
        dummy_request.user = basic_user
        context = {
            'request': dummy_request
        }
        data = {
            'name': 'Demo Test Name'
        }
        serializer = self.serializer_class(data=data, context=context)
        serializer.is_valid(raise_exception=True)
        transporter = serializer.save(user=basic_user)
        response = serializer.data
        expected = {
            'name': 'Demo Test Name',
            'slug_name': "demo-test-name",
            'rating': 0,
            'email': basic_email,
            'phone': '',
            'address': '',
            'logo': None,
        }
        assert transporter.user == basic_user
        test_case.assertDictEqual(expected, response)

    def test_transporter_create_validation(self, dummy_request, transporter):
        dummy_request.user = transporter.user
        context = {
            'request': dummy_request
        }
        data = {
            'name': 'Demo Test Name'
        }
        serializer = self.serializer_class(data=data, context=context)
        with pytest.raises(
            ValidationError, match='User already owns a transport account'
        ):
            serializer.is_valid(raise_exception=True)

    def test_transporter_validate_name(self, dummy_request, basic_user):
        dummy_request.user = basic_user
        context = {
            'request': dummy_request
        }
        data = {
            'name': 'Demo &(&) Name'
        }
        serializer = self.serializer_class(data=data, context=context)
        with pytest.raises(
            ValidationError, match='Must not contain special characters'
        ):
            serializer.is_valid(raise_exception=True)

    def test_transporter_update(self, test_case: U, transporter):
        data = {
            'name': 'New Demo Test Name'
        }
        serializer = self.serializer_class(data=data, instance=transporter)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        response = serializer.data
        expected = {
            'name': 'New Demo Test Name',
            'slug_name': "django-test-transporter",
            'rating': 0,
            'email': transporter_email,
            'phone': '',
            'address': '',
            'logo': None,
        }
        test_case.assertDictEqual(expected, response)


@pytest.mark.django_db
class TestVehicleSerializer():
    serializer_class = serializers.VehicleSerializer

    def test_serializer_response(self, vehicle):
        """Test if with_x fields are returned in response"""
        serializer = self.serializer_class(instance=vehicle)
        checks = {
            'with_tv': False,
            'with_tint': False,
            "with_ac": True,
        }
        response = serializer.data
        for key in checks:
            assert response[key] == checks[key]

    def test_create(self, transporter, file_upload):
        data = {
            "with_ac": True,
            "name": "string",
            "kind": "bike",
            "tag": "string",
            "plate_number": "string",
            "capacity": 1,
            "active": True,
            "send_mail_verification": True,
            'proof_of_ownership': file_upload
        }
        serializer = self.serializer_class(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save(transporter=transporter)
        assert serializer.data

    @pytest.mark.parametrize(
        'name, value, code',
        [
            ('name', '', 'blank'),
            ('kind', '', 'invalid_choice'),
            ('tag', '', 'blank'),
            ('plate_number', '', 'blank'),
            ('proof_of_ownership', '', 'invalid'),
            ('name', None, 'required'),
            ('kind', None, 'required'),
            ('tag', None, 'required'),
            ('plate_number', None, 'required'),
            ('proof_of_ownership', None, 'required'),
        ]
    )
    def test_validation(self, file_upload, name, value, code):
        data = {
            "with_ac": True,
            "name": "string",
            "kind": "bike",
            "tag": "string",
            "plate_number": "string",
            "capacity": 1,
            "active": True,
            "send_mail_verification": True,
            'proof_of_ownership': file_upload
        }
        if value is None:
            data.pop(name)
        else:
            data[name] = value
        serializer = self.serializer_class(data=data)
        with pytest.raises(ValidationError) as e:
            serializer.is_valid(raise_exception=True)
        assert e.value.get_codes()[name][0] == code

    @pytest.mark.parametrize(
        'name, value',
        [
            ('name', 'New name'),
            ('kind', 'bus'),
            ('tag', 'test-1'),
            ('plate_number', 'test98232'),
            ('with_ac', False),
            ('active', False),
            ('send_mail_verification', False),
            ('capacity', 200),
        ]
    )
    def test_update(self, vehicle, file_upload, name, value):
        data = {
            "with_ac": True,
            "name": "string",
            "kind": "bike",
            "tag": "string",
            "plate_number": "string",
            "capacity": 1,
            "active": True,
            "send_mail_verification": True,
            'proof_of_ownership': file_upload
        }
        data[name] = value
        serializer = self.serializer_class(data=data, instance=vehicle)
        serializer.is_valid(raise_exception=True)
        vehicle = serializer.save()

        response = serializer.data
        assert response
        assert response[name] == value


@pytest.mark.django_db
class TestTransporterUploadLogoSerializer():
    serializer_class = serializers.TransporterUploadLogo

    def test_upload(self, transporter, file_upload):
        data = {
            'logo': file_upload
        }
        serializer = self.serializer_class(instance=transporter, data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        assert transporter.user.profile.image.path


@pytest.mark.django_db
class TestTripTemplateSerializer():
    serializer_class = serializers.TripTemplateSerializer
    keys = ['vehicle_name', 'driver_name', 'tracking_code', 'created', 'trip_type', 'origin', 'destination', 'boarding_point', 'alighting_point', 'take_off_time', 'duration', 'amount', 'pre_booked_seats', 'start_date', 'recurring'] # noqa

    base_data = {
        'trip_type': 'intracity',
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

    def test_create_tripplaning(self, transporter, vehicle, driver):
        data = {
            'driver': driver.pk,
            'vehicle': vehicle.pk,
        }
        data.update(self.base_data)

        serializer = self.serializer_class(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save(transporter=transporter)

        assert serializer.data

    def test_update_tripplaning(self, trip_plan, driver, vehicle):
        data = {
            'driver': driver.pk,
            'vehicle': vehicle.pk,
        }
        data.update(self.base_data)

        serializer = self.serializer_class(trip_plan, data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        assert serializer.data

    def test_partial_update_tripplaning(self, trip_plan):
        data = {
            'destination': 'Ibadan',
            'boarding_point': 'Ojota',
            'alighting_point': 'Iwo Road',
            'take_off_time': datetime.time(4, 4, 4),
            'duration': datetime.timedelta(hours=5),
        }

        serializer = self.serializer_class(trip_plan, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        assert serializer.data

    @pytest.mark.parametrize(
        "key, value, code",
        [
            (
                'driver',
                pytest.lazy_fixture('inactive_driver'),
                ErrCode.not_active
            ),
            (
                'vehicle',
                pytest.lazy_fixture('inactive_vehicle'),
                ErrCode.not_active
            ),
            (
                'driver',
                pytest.lazy_fixture('unverified_driver'),
                ErrCode.not_verified
            ),
            (
                'vehicle',
                pytest.lazy_fixture('unverified_vehicle'),
                ErrCode.not_verified
            ),
            (
                'start_date',
                datetime.date(2019, 3, 3),
                ErrCode.old_date
            ),
            (
                'pre_booked_seats',
                20,
                ErrCode.too_much_passengers
            ),
            (
                'recurring',
                'mondays',
                ErrCode.invalid_day
            ),
            (
                'recurring',
                'everydays',
                ErrCode.invalid_day
            ),
        ]
    )
    def test_validation(self, key, value, code, vehicle, driver):

        try:
            value = value.pk
        except AttributeError:
            pass

        data = {
            'driver': driver.pk,
            'vehicle': vehicle.pk,
        }
        data.update(self.base_data)
        data[key] = value

        serializer = self.serializer_class(data=data)

        with pytest.raises(ValidationError) as err:
            serializer.is_valid(raise_exception=True)

        assert err.value.get_codes()[key][0] == code
