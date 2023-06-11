import datetime
import re
from time import sleep
from typing import Type, TypeVar

import pytest
from django.db.models import QuerySet
from model_bakery import baker
from transport.models import Booking, Passenger, TripObject, TripPlan
from transport.utils.base import get_next_day_date
from utils.base.constants import TOMORROW, unit
from utils.base.general import get_day_value, capture_output
from utils.base.db import count_queries


pytestmark = pytest.mark.django_db


@pytest.mark.usefixtures("register_baker_fields")
class TestTripPlan():
    def test_get_trip_objects(self, trip_plan):
        trip_objects: QuerySet[TripObject] = trip_plan.get_trip_objects()
        assert trip_objects.count() == 5

    def test_get_pending_trips(self, trip_plan):
        trip_objects: QuerySet[TripObject] = trip_plan.get_pending_trips()
        assert trip_objects.count() == 5

    def test_creation(self, trip_plan: Type[TripPlan]):
        trip_objects: QuerySet[TripObject] = trip_plan.get_trip_objects()
        assert trip_objects.count() == 5

        weekday_value = get_day_value(trip_plan.recurring)
        for obj in trip_objects:
            assert obj.leave_date.weekday() == weekday_value

    def test_trip_create_everyday(
        self, settings, base_trip_data: dict
    ):
        trip = TripPlan(
            **base_trip_data,
            pre_booked_seats=4,
            start_date=datetime.date.today(),
            recurring=settings.EVERYDAY,
        )
        trip.save()
        trip_objects: QuerySet[TripObject] = trip.get_trip_objects()
        assert trip_objects.count() == 30

    def test_trip_create_no_recurring(
        self, base_trip_data: dict
    ):
        trip = TripPlan(
            **base_trip_data,
            pre_booked_seats=4,
            start_date=datetime.date.today(),
            recurring=''
        )
        trip.save()
        trip_objects: QuerySet[TripObject] = trip.get_trip_objects()
        assert trip_objects.count() == 1

    def test_update_trip_recurring(self, trip_plan: Type[TripPlan]):
        trip_plan.recurring = 'monday'
        trip_plan.save()
        trip_objects: QuerySet[TripObject] = trip_plan.get_trip_objects()

        assert trip_objects.count() == 5

        weekday_value = get_day_value(trip_plan.recurring)
        for obj in trip_objects:
            assert obj.leave_date.weekday() == weekday_value

    def test_update_trip_start_date(self, settings, trip_plan: Type[TripPlan]):
        trip_plan.start_date = datetime.date(2022, 4, 3)
        trip_plan.save()
        trip_objects: QuerySet[TripObject] = trip_plan.get_trip_objects()

        assert trip_objects.count() == 5

        weekday_value = get_day_value(trip_plan.recurring)
        expected = get_next_day_date(
            trip_plan.start_date,
            trip_plan.recurring,
        ) + datetime.timedelta(
            days=settings.MAX_TRIP_PLANS_DAYS
        )
        for obj in trip_objects:
            assert obj.leave_date.weekday() == weekday_value
            assert obj.leave_date <= expected

    def test_update_trip_data(self, trip_plan: Type[TripPlan]):
        trip_plan.destination = 'London'
        trip_plan.save()
        trip_objects: QuerySet[TripObject] = trip_plan.get_trip_objects()

        assert trip_objects.count() == 5

        for obj in trip_objects:
            assert obj.destination == 'London'

    def test_get_clone_data(self, trip_plan: Type[TripPlan], base_trip_data):
        base_trip_data['passengers_count'] = trip_plan.pre_booked_seats
        unit.assertDictContainsSubset(
            base_trip_data,
            trip_plan.get_clone_data(),
        )

    def test_create_trip_object(self, trip_plan: Type[TripPlan]):
        date = datetime.date(2022, 9, 12)
        trip_object = trip_plan.create_trip_object(date)
        assert trip_object.leave_date == date

        trip_plan.get_trip_objects().get(
            id=trip_object.id
        )

    def test_stabilize_trip_objects(self, old_trip_plan: Type[TripPlan]):
        trip_objects: QuerySet[TripObject] = old_trip_plan.get_trip_objects()
        assert trip_objects.count() == 5

        old_trip_plan.stabilize_trip_objects()

        trip_objects: QuerySet[TripObject] = old_trip_plan.get_trip_objects()
        assert trip_objects.count() == 5

    def test_generate_trips(self, trip_plan: Type[TripPlan]):
        trip_objects: QuerySet[TripObject] = trip_plan.get_trip_objects()
        assert trip_objects.count() == 5

        trip_plan.generate_trips(datetime.date(
            2023, 4, 5
        ))

        trip_objects: QuerySet[TripObject] = trip_plan.get_trip_objects()
        assert trip_objects.count() == 10

    def test_delete_tripplaning(self, trip_plan: Type[TripPlan]):
        pk = trip_plan.pk
        trip_plan.delete()
        trip_objects: QuerySet[TripObject] = TripObject.objects.filter(
            plan__pk=pk)
        assert trip_objects.count() == 0


_T = TypeVar(name='_T', bound=TripObject)


class TestTripObject():

    passengers_count = 2

    # Utils
    def create_bookings(self, trip):
        for state in ('confirmed', 'unconfirmed'):
            baker.make(
                Booking,
                trip=trip,
                state=state
            )

    def create_passengers(self, trip):
        booking = baker.make(
            Booking,
            trip=trip,
            state='confirmed'
        )
        baker.make(
            Passenger,
            booking=booking,
            _quantity=self.passengers_count
        )

    def create_rbookings(self, trip):
        ratings = (5, 4)
        for rating in ratings:
            baker.make(
                Booking,
                trip=trip,
                rating=rating
            )
        return sum(ratings) / 2

    def test_create(self, trip_object):
        assert trip_object.id

    def test_create_booking(self, basic_user, trip_object: _T):
        booking = trip_object.create_booking(user=basic_user)
        assert booking.id
        assert booking.trip == trip_object

    def test_update_transporter_ratings(self, trip_object: _T):
        trip_object.rating = 5
        trip_object.save()
        assert trip_object.transporter.rating == 5

    @pytest.mark.xfail
    def test_get_ticket_html(self):
        pass

    @pytest.mark.xfail
    def test_send_ticket_message(self):
        pass

    def test_has_started(self, trip_object: _T):
        assert trip_object.has_started() is False

    def test_has_started_true(self, trip_object: _T):
        baker.make(
            Booking,
            trip=trip_object,
            state='confirmed'
        )
        assert trip_object.has_started()

    def test_get_bookings(self, trip_object: _T):
        self.create_bookings(trip_object)
        assert trip_object.get_bookings().count() == 2

    def test_get_unconfirmed_bookings(self, trip_object: _T):
        self.create_bookings(trip_object)
        assert trip_object.get_unconfirmed_bookings().count() == 1

    def test_get_confirmed_bookings(self, trip_object: _T):
        self.create_bookings(trip_object)
        assert trip_object.get_confirmed_bookings().count() == 1

    def test_get_cancelled_bookings(self, trip_object: _T):
        self.create_bookings(trip_object)
        assert trip_object.get_cancelled_bookings().count() == 0

    def test_get_passengers_zero(self, trip_object: _T):
        self.create_bookings(trip_object)
        assert trip_object.get_passengers().count() == 0

    def test_update_available_seats_initial(self, trip_object: _T):
        self.create_bookings(trip_object)
        assert trip_object.available_seats == (
            trip_object.vehicle.capacity - trip_object.passengers_count
        )

    def test_get_passengers_none(self, trip_object: _T):
        assert trip_object.get_passengers() is None

    def test_get_passengers(self, trip_object: _T):
        self.create_passengers(trip_object)
        assert trip_object.get_passengers().count() == self.passengers_count

    def test_update_available_seats(self, trip_object: _T):
        prev_passengers_count = trip_object.passengers_count
        passengers_count = prev_passengers_count + self.passengers_count
        self.create_passengers(trip_object)
        assert trip_object.available_seats == (
            trip_object.vehicle.capacity - passengers_count
        )

    def test_get_count_passengers(self, trip_object: _T):
        prev_passengers_count = trip_object.passengers_count
        expected = prev_passengers_count + self.passengers_count
        self.create_passengers(trip_object)
        assert trip_object.get_count_passengers() == expected

    def test_get_count_passengers_none(self, trip_object: _T):
        prev_passengers_count = trip_object.passengers_count
        assert trip_object.get_count_passengers() == prev_passengers_count

    def test_get_trip_id(self, trip_object: _T):
        assert trip_object.get_trip_id() == trip_object.tracking_code

    def test_calculate_rating(self, trip_object: _T):
        expected_rating = self.create_rbookings(trip_object)
        assert trip_object.calculate_rating() == expected_rating

    def test_calculate_rating_zero(self, trip_object: _T):
        self.create_bookings(trip_object)
        assert trip_object.calculate_rating() == 0

    def test_calculate_rating_null(self, trip_object: _T):
        assert trip_object.calculate_rating() == 0

    def test_update_ratings(self, trip_object: _T):
        expected_rating = self.create_rbookings(trip_object)
        trip_object.update_ratings()
        assert trip_object.rating == expected_rating
        assert trip_object.transporter.rating == expected_rating


class TestTripObjectManager():

    def create_state_trips(self, data):
        data["leave_date"] = TOMORROW
        data["passengers_count"] = 4

        states = ('pending', 'started', 'completed', 'cancelled')
        for state in states:
            baker.make(
                TripObject,
                state=state,
                **data
            )

    def test_get_pending(self, base_trip_data):
        self.create_state_trips(base_trip_data)
        assert TripObject.objects.get_pending().count() == 1

    def test_get_started(self, base_trip_data):
        self.create_state_trips(base_trip_data)
        assert TripObject.objects.get_started().count() == 1

    def test_get_completed(self, base_trip_data):
        self.create_state_trips(base_trip_data)
        assert TripObject.objects.get_completed().count() == 1

    def test_get_cancelled(self, base_trip_data):
        self.create_state_trips(base_trip_data)
        assert TripObject.objects.get_cancelled().count() == 1

    @pytest.mark.usefixtures("create_search_trips")
    @pytest.mark.parametrize(
        'query, expected',
        [
            (
                {
                    "origin": "Lagos, ojota",
                    "destination": "Ibadan",
                    "leave_date": TOMORROW,
                    "passengers": 1,
                }, 2
            ),
            (
                {
                    "origin": "Lagos",
                    "destination": "Ibadan",
                    "leave_date": TOMORROW,
                    "passengers": 3,
                }, 2
            ),
            (
                {
                    "origin": "Oyo",
                    "destination": "Ogun",
                    "leave_date": TOMORROW,
                    "passengers": 3,
                    "min_take_off_time": datetime.time(2),
                    "max_take_off_time": datetime.time(14, 15),
                }, 2
            ),
            (
                {
                    "origin": "Akure",
                    "destination": "Ibadan",
                    "leave_date": TOMORROW,
                    "passengers": 3,
                    "max_amount": 5000,
                }, 1
            ),
            (
                {
                    "origin": "Oyo",
                    "destination": "Ogun",
                    "leave_date": TOMORROW,
                    "passengers": 3,
                    "min_take_off_time": datetime.time(2),
                    "max_amount": 6000,
                    "vehicle_type": "plane",
                }, 1
            ),
            (
                {
                    "origin": "Lagos",
                    "destination": "Oyo",
                    "leave_date": TOMORROW,
                    "passengers": 1,
                    "preferences": {
                        "with_ac": True,
                        "with_tv": False,
                    }
                }, 1
            ),
        ]
    )
    def test_search(self, query, expected):
        results = TripObject.objects.find_trips(**query)
        assert results.count() == expected

    @pytest.mark.usefixtures("create_search_trips")
    def test_search_cache(self, settings):
        settings.SEARCH_TRIPS_CACHE_TIME_IN_SECONDS = 1
        query = {
            "origin": "Lagos, ojota",
            "destination": "Ibadan",
            "leave_date": TOMORROW,
            "passengers": 2,
        }

        @count_queries()
        def call():
            TripObject.objects.find_trips(**query)

        def assert_value(expected, output):
            pattern = re.compile(r"Ran (\d) queries?")
            match = pattern.search(output)
            assert match
            assert match.groups()[0] == expected

        for expected in ("1", "0"):
            with capture_output(call) as output:
                assert_value(expected, output)

        sleep(1)
        with capture_output(call) as output:
            assert_value("1", output)


class TestVehicleModel():
    pass
