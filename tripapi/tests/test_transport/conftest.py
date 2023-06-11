from copy import copy, deepcopy
import datetime
from pathlib import Path
from typing import List, TypeVar

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from transport.models import Driver, TripPlan, Vehicle, TripObject
from account.models import User
from utils.base.constants import TOMORROW
from model_bakery import baker

T = TypeVar('T', bound=Path)


@pytest.fixture
def baked_trips():
    return baker.make(
        TripObject,
        _quantity=5,
        _bulk_create=True
    )


@pytest.fixture
def file_path(settings):
    return settings.BASE_DIR / 'test_files/file1.png'


@pytest.fixture
def file_upload(file_path: T):
    return SimpleUploadedFile(
        "file.png", file_path.read_bytes())


@pytest.fixture
def vehicle_obj(transporter, file_upload):
    data = {
        "with_ac": True,
        "name": "string",
        "kind": "bike",
        "tag": "string",
        "plate_number": "string",
        "capacity": 10,
        "active": True,
        "send_mail_verification": True,
        'proof_of_ownership': file_upload,
        'transporter': transporter,
        "verified": True,
    }
    return Vehicle(**data)


@pytest.fixture
def vehicle(vehicle_obj):
    obj = deepcopy(vehicle_obj)
    obj.save()
    return obj


@pytest.fixture
def base_driver(transporter, basic_user, file_upload):
    basic_user.pk = None
    basic_user.email = 'driver@test.com'
    basic_user.save()
    user = User.objects.get(pk=basic_user.pk)
    data = {
        "user": user,
        "transporter": transporter,
        "licence": file_upload,
        "id_card": file_upload,
        "active": True,
        "send_mail_verification": True,
        "verified": True,
    }
    return Driver(**data)


@pytest.fixture
def driver(base_driver):
    base_driver.save()
    return base_driver


@pytest.fixture
def inactive_driver(base_driver):
    base_driver.active = False
    base_driver.save()
    return base_driver


@pytest.fixture
def inactive_vehicle(vehicle_obj):
    vehicle_obj.active = False
    vehicle_obj.save()
    return vehicle_obj


@pytest.fixture
def unverified_driver(base_driver):
    base_driver.verified = False
    base_driver.save()
    return base_driver


@pytest.fixture
def unverified_vehicle(vehicle_obj):
    vehicle_obj.verified = False
    vehicle_obj.save()
    return vehicle_obj


@pytest.fixture
def trip_data_base(transporter, driver):
    return {
        'trip_type': 'intracity',
        'transporter': transporter,
        'driver': driver,
        'origin': 'Lagos',
        'destination': 'Ibadan',
        'boarding_point': 'Ojota',
        'alighting_point': 'Iwo Road',
        'take_off_time': datetime.time(4, 4, 4),
        'duration': datetime.timedelta(hours=5),
        'amount': 5000,
    }


@pytest.fixture
def base_trip_data(trip_data_base, vehicle):
    trip_data_base['vehicle'] = vehicle
    return trip_data_base


@pytest.fixture
def base_trip_object(base_trip_data):
    trip = TripObject(
        **base_trip_data,
        passengers_count=4,
        leave_date=TOMORROW,
    )
    return trip


@pytest.fixture
def trip_object(base_trip_object):
    base_trip_object.save()
    return base_trip_object


@pytest.fixture
def base_trip_plan(base_trip_data):
    trip = TripPlan(
        **base_trip_data,
        pre_booked_seats=4,
        start_date=datetime.date.today(),
        recurring='saturday',
    )
    return trip


@pytest.fixture
def trip_plan(base_trip_plan):
    base_trip_plan.save()
    return base_trip_plan


@pytest.fixture
def trip(trip_plan):
    return trip_plan.get_trip_objects().first()


@pytest.fixture
def old_trip_plan(base_trip_data):
    trip = TripPlan(
        **base_trip_data,
        pre_booked_seats=4,
        recurring='saturday',
        start_date=datetime.date(2022, 8, 3)
    )
    trip.save()
    return trip


trip_keys = (
    "origin", "destination", "leave_date", "passengers_count",
    "take_off_time", "amount", ("kind", "specifications"))
trip_maps = (
    ('Lagos, Ojota', 'Oyo, Ibadan', 1, 8, (4, 5), 120, ("bike", {
        "with_ac": False,
        "with_tv": True,
        "with_tint": False,
    })),
    ('Lagos, Ikorodu', 'Oyo, Ibadan', 1, 5, (11, 5), 150, ("bus", {
        "with_ac": True,
        "with_tv": False,
        "with_tint": True,
    })),
    ('Lagos, Ojota', 'Oyo, Ibadan Central', 1, 1, (4, 5), 90, ("train", {
        "with_ac": True,
        "with_tv": True,
        "with_tint": False,
    })),
    ('Lagos, Ojota', 'Oyo, Ibadan East', 2, 8, (19, 50), 1200, ("train", {
        "with_ac": True,
        "with_tv": True,
        "with_tint": False,
    })),
    ('Lagos, Surulere', 'Port Harcourt, Ketu', 2, 8, (4, 5), 500, ("bus", {
        "with_ac": False,
        "with_tv": True,
        "with_tint": True,
    })),
    ('Oyo, Ibadan', 'Ogun, Ikenne', 1, 5, (14, 15), 1200, ("bus", {
        "with_ac": True,
        "with_tv": True,
        "with_tint": False,
    })),
    ('Oyo, Ibadan', 'Ogun, Ijebu', 1, 3, (2, 30), 320, ("plane", {
        "with_ac": True,
        "with_tv": False,
        "with_tint": True,
    })),
    ('Oyo, Iseyin', 'Ogun, Hassan', 1, 2, (14, 25), 5120, ("bus", {
        "with_ac": False,
        "with_tv": True,
        "with_tint": True,
    })),
    ('Akure, Futa', 'Kwara, Ilorin', 1, 5, (13, 15), 6120, ("bus", {
        "with_ac": True,
        "with_tv": True,
        "with_tint": False,
    })),
    ('Akure, Futa', 'Oyo, Ibadan', 1, 3, (17, 45), 1260, ("bus", {
        "with_ac": True,
        "with_tv": False,
        "with_tint": True,
    })),
    ('Akure, Ilesha', 'Oyo, Ibadan Central', 1, 4, (2, 23), 7820, ("bus", {
        "with_ac": True,
        "with_tv": True,
        "with_tint": False,
    })),
)


@pytest.fixture
def create_search_trips(trip_data_base: dict, vehicle_obj: Vehicle):

    trips = []

    trip_index = 0

    process_value = {
        "take_off_time": lambda value: datetime.time(*value),
        "leave_date": lambda value: datetime.date.today() + datetime.timedelta(days=value),  # noqa
    }

    for trip_values in trip_maps:
        trip = TripObject()
        trip._meta.get_field("tracking_code").pre_save(trip, True)

        vehicle = copy(vehicle_obj)

        for key, value in trip_data_base.items():
            setattr(trip, key, value)

        for key, value in zip(trip_keys, trip_values):

            process_func = process_value.get(key, None)
            if process_func is not None:
                value = process_func(value)

            elif isinstance(key, tuple):

                for k, v in zip(key, value):
                    setattr(vehicle, k, v)

                setattr(vehicle, "tag", f"string{trip_index}")
                setattr(vehicle, "plate_number", f"string{trip_index}")
                vehicle.save()

                key = 'vehicle'
                value = vehicle

            setattr(trip, key, value)

        trips.append(trip)
        trip_index += 1

    created_trips: List[TripObject] = TripObject.objects.bulk_create(trips)

    for trip in created_trips:
        trip.update_available_seats()
        trip.save()

    # Asserts to test results
    assert TripObject.objects.count() == 11
    assert Vehicle.objects.count() == 11
