import json
import os
import shutil
from copy import deepcopy
from datetime import date, time, datetime
from pathlib import PurePath
from typing import Type

from django.conf import settings
from django.core.validators import MaxValueValidator
from django.db import models
from django.db.models.query import QuerySet
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils.text import slugify
from django_hint import QueryType
from payment.models import BankAccount

from utils.base.fields import TrackingCodeField
from utils.base.general import (add_queryset, driver_upload_path_idcard,
                                driver_upload_path_licence, get_model_fields,
                                merge_querysets, split_datetime, today,
                                vehicle_upload_path)
from utils.base.mixins import CreatedMixin, ModelChangeFunc
from utils.base.validators import (validate_phone, validate_rating_level,
                                   validate_special_char)

from .managers import BookingManager, TripManager, VehicleManager
from .utils.base import generate_next_n_days
from .validators import (validate_active, validate_passengers_count,
                         validate_recurring_data, validate_start_date,
                         validate_verified)

# NOTE: When writing cron jobs, it should only run for trip plans
# that have a recurring value
# When trip plannings are deleted or updated, send mails to child bookings
# refund them, when they are cancelled too

# TODO: Rate transporters on amount of confirmed bookings, approved, cancelled
# and normal ratings


class Transporter(models.Model):
    """
    Transporter partners model
    """
    user = models.OneToOneField('account.User', on_delete=models.CASCADE)

    name = models.CharField(
        max_length=100,
        validators=[validate_special_char],
        unique=True)

    slug_name = models.SlugField(unique=True, max_length=200)
    rating = models.FloatField(default=0.0, validators=[validate_rating_level])

    def get_trips(self) -> QueryType['TripObject']:
        return self.tripobject_set.all()

    def get_pending_trips(self) -> QueryType['TripObject']:
        return self.get_trips().get_pending_trips()

    def get_bookings(self) -> QuerySet:
        trips = self.get_trips()
        if trips:
            querysets = [
                trip.get_bookings()
                for trip in trips]
            return merge_querysets(*querysets)
        return Booking.objects.none()

    def get_unconfirmed_bookings(self) -> QuerySet:
        return self.get_bookings().get_unconfirmed_bookings()

    def get_confirmed_bookings(self) -> QuerySet:
        return self.get_bookings().get_confirmed_bookings()

    def get_cancelled_bookings(self) -> QuerySet:
        return self.get_bookings().get_cancelled_bookings()

    def update_ratings(self):
        self.rating = self.calculate_rating()

    def calculate_rating(self) -> float:
        """
        Get the avg ratings from the bookings
        """

        total, length = 0, 0

        for trip in self.get_trips():
            total += trip.rating
            length += 1

        return total / (length or 1)

    def save(self, *args, **kwargs):
        # Create slug name
        if not self.id:
            self.slug_name = slugify(self.name)
            super().save(*args, **kwargs)
            BankAccount.objects.create(user=self.user)
            return
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Driver(models.Model):
    """
    Transporter's drivers model
    """
    tracking_code = TrackingCodeField(prefix="DVR")
    user = models.OneToOneField('account.User', on_delete=models.CASCADE)
    transporter = models.ForeignKey(Transporter, on_delete=models.CASCADE)
    verified = models.BooleanField(default=False)

    licence = models.ImageField(
        upload_to=driver_upload_path_licence, null=True, blank=True)

    id_card = models.ImageField(
        upload_to=driver_upload_path_idcard, null=True, blank=True)

    active = models.BooleanField(default=False)
    send_mail_verification = models.BooleanField(default=False)

    def get_trips_added(self) -> int:
        """
        Get number of trips booked with this driver

        :return: connected trips
        :rtype: int
        """
        return self.tripobject_set.count()

    def __str__(self):
        return self.user.profile.fullname


class Vehicle(models.Model):
    """
    Model for Transporter's added vehicles
    """

    VEHICLE_TYPE = (
        ('bike', 'Bike'),
        ('bus', 'Bus'),
        ('train', 'Train'),
        ('plane', 'Plane'),
    )
    transporter = models.ForeignKey(Transporter, on_delete=models.CASCADE)
    verified = models.BooleanField(default=False)

    name = models.CharField(
        max_length=100, validators=[validate_special_char])

    kind = models.CharField(choices=VEHICLE_TYPE, max_length=20)

    tag = models.SlugField(unique=True)

    proof_of_ownership = models.FileField(
        upload_to=vehicle_upload_path)

    plate_number = models.CharField(
        max_length=20, unique=True,
        error_messages={
            'unique': 'Plate number has already been used by another vehicle'
        })

    capacity = models.PositiveSmallIntegerField(
        default=1, validators=[MaxValueValidator(500)],
        help_text='Amount of passengers that can be in vehicle')

    active = models.BooleanField(default=False)
    send_mail_verification = models.BooleanField(default=False)

    # Vehicle specification fields
    specifications = models.JSONField(null=True)
    __specification_fields = [
        {
            'name': 'with_ac',
            'help_text': 'Specify if the vehicle as an Air Conditioner'
        },
        {
            'name': 'with_tv',
            'help_text': 'Specify if the vehicle as a Television'
        },
        {
            'name': 'with_tint',
            'help_text': 'Specify if the vehicle as Tinted Windows'
        },
    ]

    def create_function(template: str, key: str, **kwargs):
        """
        Dynamically create a getter or setter
        function for specification keys for setting
        and getting values on and from specification keys

        :param template: setter or getter
        :type template: str
        :param key: key for specifications
        :type key: str
        :return: setter or getter function
        :rtype: function
        """
        if template == 'getter':
            def template(self):
                return getattr(self, f'_{key}')
            return template
        elif template == 'setter':
            def template(self, value):
                self.set_specification_value(key, value)
                setattr(self, f'_{key}', value)
            return template

    @classmethod
    def format_init_data(cls, data: dict):
        if data:
            data = deepcopy(data)
            internal = {}
            for key in cls.get_specification_keys():
                value = data.pop(key, settings.VEHICLE_SPECIFICATION_DEFAULT)
                internal[key] = value
            data['specifications'] = internal
        return data

    def __init__(self, *args, **kwargs):
        """
        Add new property for specifications keys on
        instance with properties having setters and
        getters functions dynamically.
        """
        format_data = self.__class__.format_init_data(kwargs)

        super().__init__(*args, **format_data)

        if isinstance(self.specifications, str):
            self.specifications = json.loads(self.specifications)

        data = self.get_specifications()
        klass = self.__class__
        for key, value in data.items():
            setattr(klass, key, property(
                klass.create_function('getter', key),
                klass.create_function('setter', key)
            ))
            setattr(self, key, value)

    objects = VehicleManager()

    @classmethod
    def get_specification_fields(cls) -> list[dict[str, str]]:
        """
        Get the __specification_fields from class

        :return: list of key value pairs of
        key names and help texts
        :rtype: list[dict[str, str]]
        """
        return cls.__specification_fields

    @classmethod
    def get_specification_keys(cls) -> list:
        """
        Return key names from specification_fields

        :return: list of key names
        :rtype: list
        """
        keys = []
        for field in cls.get_specification_fields():
            keys.append(field['name'])
        return keys

    def set_specification_value(self, key, value):
        """
        Set the key to value on specifications json field

        :param key: key name
        :type key: str
        :param value: key value
        :type value: bool
        """
        specifications = self.get_specifications()
        specifications[key] = value
        self.specifications = specifications

    def get_specifications(self):
        """
        Gets the value of all specifications into a dict
        with cleaned values if not found
        """
        clean_dict = dict()
        for key in self.get_specification_keys():
            value = self.specifications.get(
                key, settings.VEHICLE_SPECIFICATION_DEFAULT)
            clean_dict[key] = value
        return clean_dict

    def get_trips_count(self) -> int:
        """
        Get number of trips booked with vehicle

        :return: connected trips
        :rtype: int
        """
        return self.tripobject_set.count()

    def save(self, *args, **kwargs):
        """
        Slugified tags and saves it
        """
        self.tag = slugify(self.tag)
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# TODO: Vehicle and Driver must be active
class TripAbstractModel(CreatedMixin):
    """
    This will work like a template used to create
    other trips
    """

    TRIP_TYPES = (
        ('intracity', 'Intracity',),
        ('intercity', 'Intercity',),
        ('interstate', 'Interstate',),
        ('international', 'International',),
    )

    trip_type = models.CharField(choices=TRIP_TYPES, max_length=20)

    transporter: Transporter = models.ForeignKey(
        Transporter, on_delete=models.PROTECT)

    vehicle = models.ForeignKey(
        Vehicle, on_delete=models.DO_NOTHING, blank=False
    )

    driver = models.ForeignKey(
        Driver, on_delete=models.DO_NOTHING, null=True, blank=False
    )

    origin = models.CharField(
        max_length=255, help_text='Name of origin state & lga \
for trip e.g. Lagos, Ojota')

    destination = models.CharField(
        max_length=255, help_text='Name of destination state & lga \
for trip e.g. Oyo, Ibadan Central')

    boarding_point = models.CharField(
        max_length=255, help_text='Name of park or address e.g. Ojota Park')

    alighting_point = models.CharField(
        max_length=255, help_text='Name of park or address e.g. Iwo Road')

    take_off_time = models.TimeField()  # takes in datetime.time
    duration = models.DurationField()  # takes in timedelta
    amount = models.FloatField(help_text='Amount payed for trip')

    def clean(self) -> None:
        super().clean()
        if self.driver:
            validate_active(self.driver)
            validate_verified(self.driver)

        if self.vehicle:
            validate_active(self.vehicle)
            validate_verified(self.vehicle)

    class Meta:
        abstract = True

    def get_vehicle_name(self) -> str:
        """Get the vehicle name"""
        return self.vehicle.name

    def get_transporter_name(self) -> str:
        """Get the transporter name"""
        return self.transporter.name

    def get_driver_name(self) -> str:
        """Get the driver name"""
        return str(self.driver)


class TripPlan(TripAbstractModel, ModelChangeFunc):
    """
    This will be a connecting parent that
    other created trips will be connected to
    """
    tracking_code = TrackingCodeField(prefix="TRPL")

    pre_booked_seats = models.PositiveSmallIntegerField(default=0)
    start_date = models.DateField(validators=[validate_start_date])

    recurring = models.CharField(
        max_length=16, null=True, blank=True,
        validators=[validate_recurring_data])

    def get_pending_trips(self) -> QuerySet['TripObject']:
        return self.tripobject_set.get_pending()

    def similarize_data_on_trips(self):
        """
        Meant to update unstarted trips to look like template,
        will be called for updates on trip template only
        """
        trips = self.get_pending_trips()
        data = self.get_clone_data()
        for trip in trips:
            for key, value in data.items():
                setattr(trip, key, value)
            trip.save()

    def delete_inactive_trips(self):
        """Delete trips that have not started"""
        trips = self.get_trip_objects()
        for trip in trips:
            if not trip.has_started():
                trip.delete()

    def update_trip_plans(self):
        """Delete unbooked trip plans when recurring changes
        and create new ones with the new recurring days"""
        self.delete_inactive_trips()
        self.stabilize_trip_objects()

    def update_trips_leave_dates(self):
        """Delete unbooked trip plans when start date changes
        and create new ones with the new leave dates"""
        self.delete_inactive_trips()
        self.generate_trips()

    monitor_change = {
        'recurring': update_trip_plans,
        'start_date': update_trips_leave_dates,
    }

    def get_trip_objects(self) -> QuerySet['TripObject']:
        return self.tripobject_set.all()

    def get_clone_data(self) -> dict:
        """Get the clone data to use to
        create a new trip plan object"""
        fields = get_model_fields(TripAbstractModel)
        data = {}
        for field in fields:
            data[field] = getattr(self, field)
        data['passengers_count'] = self.pre_booked_seats
        return data

    def create_trip_object(self, leave_date: date) -> Type['TripObject']:
        """Create a new trip object from this template"""
        data = self.get_clone_data()
        data['leave_date'] = leave_date
        return self.tripobject_set.create(**data)

    def stabilize_trip_objects(self):
        """
        Creates new trips for trip plan template such that
        it stabilizes it to `max_trip_days` amount of trips.
        That is, it just makes sure that in the next `max_trip_days`
        there must be trips filled in to the max amount that can
        be there. And old trips before today is deleted
        """
        self.generate_trips(today())
        old_trips = self.get_trip_objects().filter(leave_date__lt=today())
        for trip in old_trips:
            if not trip.has_started():
                trip.delete()

    def generate_trips(self, start_date=None):
        """This will create new trips for this trip template with unique
        leave dates"""
        if start_date is None:
            start_date = self.start_date

        if self.recurring:
            dates = generate_next_n_days(start_date, self.recurring)
        else:
            dates = [start_date]

        for _date in dates:
            has_leave_date = self.get_trip_objects().filter(
                leave_date=_date).exists()
            if not has_leave_date:
                self.create_trip_object(_date)

    def clean_passengers(self) -> None:
        validate_passengers_count(self.pre_booked_seats, self.vehicle.capacity)

    def save(self, *args, **kwargs):
        self.clean_passengers()
        if not self.id:
            # Just Created
            super().save(*args, **kwargs)

            # Create new trip plans
            # Get leave dates for plans to be created
            self.generate_trips()
            return

        self.similarize_data_on_trips()
        super().save(*args, **kwargs)


# TODO: Passengers on a trip can't passed vehicle max seats
class TripObject(TripAbstractModel, ModelChangeFunc):
    """
    This is a single trip connected to a TripPlan
    """
    tracking_code = TrackingCodeField(prefix="TRIP")

    TRIP_STATUS = (
        ('pending', 'Pending',),
        ('started', 'In transit',),
        ('completed', 'Completed',),
        ('cancelled', 'Cancelled',),
    )

    plan = models.ForeignKey(
        TripPlan, on_delete=models.DO_NOTHING, null=True)

    leave_date = models.DateField()
    passengers_count = models.PositiveBigIntegerField(default=0)
    available_seats = models.PositiveBigIntegerField(default=0)
    state = models.CharField(
        choices=TRIP_STATUS, max_length=50, default='pending')

    rating = models.FloatField(
        default=0.0, validators=[validate_rating_level])

    objects: TripManager = TripManager()

    def update_transporter_ratings(self):
        """Update transporter ratings"""
        self.transporter.update_ratings()
        self.transporter.save()

    def update_available_seats(self):
        """Update number of available seats for a vehicle"""
        self.available_seats = self.vehicle.capacity - \
            self.passengers_count
        if self.available_seats < 0:
            raise ValueError(
                "Vehicle capacity is not enough for passengers")

    monitor_change = {
        'rating': update_transporter_ratings,
        'vehicle': update_available_seats,
        'passengers_count': update_available_seats,
    }

    def get_arrival_time(self) -> time:
        """Get the arrival time of a trip"""
        dt = datetime.combine(
            self.leave_date, self.take_off_time) + self.duration
        return dt.time()

    def save(self, *args, **kwargs):
        if not self.id:
            self.available_seats = self.vehicle.capacity - \
                self.passengers_count
        super().save(*args, **kwargs)

    def get_ticket_html(self):
        """Build the html ticket message"""

    def send_ticket_message(self):
        """Send ticket message to user"""

    def has_started(self):
        """Check if trip plan has been booked"""
        return self.get_confirmed_bookings().exists()

    def get_bookings(self) -> QuerySet['Booking']:
        return self.booking_set.all()

    def get_unconfirmed_bookings(self) -> QuerySet['Booking']:
        return self.get_bookings().get_unconfirmed_bookings()

    def get_confirmed_bookings(self) -> QuerySet['Booking']:
        return self.get_bookings().get_confirmed_bookings()

    def get_cancelled_bookings(self) -> QuerySet['Booking']:
        return self.get_bookings().get_cancelled_bookings()

    def get_passengers(self):
        """
        Returns the passengers attached to
        confirmed bookings of this trip
        """
        sets = None

        for booking in self.get_confirmed_bookings():
            queryset = booking.get_passengers()
            if sets is None:
                sets = queryset
            else:
                sets = add_queryset(sets, queryset)

        return sets

    def get_count_passengers(self) -> int:
        """
        Returns amount of passengers on trip
        """
        return self.passengers_count

    def get_trip_id(self) -> str:
        """
        Returns the trip code
        """
        return self.tracking_code

    def update_ratings(self, commit=True):
        """Recalculate this trip rating and update it"""
        self.rating = self.calculate_rating()
        if commit:
            self.save()

    def calculate_rating(self) -> float:
        """
        Get the avg ratings from trip bookings
        """
        total, length = 0, 0

        for booking in self.get_bookings():
            total += booking.rating
            length += 1

        return total / (length or 1)

    def create_booking(self, **kwargs):
        """Create a booking"""
        return self.booking_set.create(**kwargs)


class Booking(ModelChangeFunc, CreatedMixin):
    """
    Database model for bookings created by users
    """

    BOOKING_STATUS = (
        ('unconfirmed', 'Unconfirmed',),
        ('confirmed', 'Confirmed',),
        ('cancelled', 'Cancelled',),
    )

    tracking_code = TrackingCodeField(prefix="BKG")
    trip: TripObject = models.ForeignKey(
        TripObject, on_delete=models.DO_NOTHING)

    user = models.OneToOneField('account.User', on_delete=models.CASCADE)
    state = models.CharField(
        choices=BOOKING_STATUS, default='unconfirmed', max_length=40)
    rating = models.FloatField(
        default=0.0, validators=[validate_rating_level])

    objects = BookingManager()

    def update_trip(self):
        self.trip.update_ratings()

    monitor_change = {
        'rating': update_trip,
    }

    def get_tx_tracking_code(self) -> str:
        """Get the transaction tracking code"""
        return self.tracking_code

    def get_transaction(self):
        """
        Get the transaction for the order
        """
        if not self.transaction:
            raise ValueError('Transaction not found')
        return self.transaction

    def update_success(self):
        """
        Process order after successful payment
        """
        transaction = self.get_transaction()
        paid_at = transaction.paidAt  # noqa

    def get_passengers(self) -> QuerySet:
        return self.passenger_set.all()

    def set_confirmed(self):
        """Confirm this booking"""

    def create_passenger(
        self, first_name, last_name, send_tips,
        email='', phone='', medical_information=''
    ):
        """Creates a new passenger to booking"""

    def create_transaction(self):
        """Get or create a transaction for this booking"""

    def get_booking_code(self) -> str:
        """
        Returns the booking code
        """
        return self.tracking_code

    def update_ratings(self):
        self.rating = self.calculate_rating()

    def calculate_rating(self) -> float:
        """
        Get the avg ratings from the passengers
        """
        total, length = 0, 0
        for passenger in self.get_passengers():
            total += passenger.get_rating()
            length += 1

        return total / (length or 1)

    def get_created_date(self) -> str:
        return split_datetime(self.created)[0]

    def get_created_time(self) -> str:
        return split_datetime(self.created)[1]

    def __str__(self) -> str:
        return str(self.user)


class Passenger(models.Model):
    """
    Passengers details for bookings
    """

    booking: Booking = models.ForeignKey(Booking, on_delete=models.CASCADE)

    first_name = models.CharField(
        max_length=30, validators=[validate_special_char])

    last_name = models.CharField(
        max_length=30, validators=[validate_special_char])

    email = models.EmailField(blank=True)
    phone = models.CharField(
        blank=True, validators=[validate_phone], max_length=20)
    medical_information = models.TextField()
    send_tips = models.BooleanField(default=False)

    def get_rating(self):
        """
        Get the rating from the review
        """
        try:
            return self.review.rating
        except Review.DoesNotExist:
            pass
        return 0

    def get_fullname(self):
        """
        Returns the fullname of passenger
        """
        return f"{self.last_name} {self.first_name}".capitalize()

    def save(self, *args, **kwargs):
        if not self.id:
            super().save(*args, **kwargs)
            self.booking.trip.passengers_count += 1
            self.booking.trip.save()
            return
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        data = super().delete(*args, **kwargs)
        self.booking.trip.passengers_count -= 1
        self.booking.trip.save()
        return data

    def __str__(self):
        return self.get_fullname()


class Review(CreatedMixin):
    """
    Reveiw for Transporters from Booking
    """

    passenger: Passenger = models.OneToOneField(
        Passenger, on_delete=models.CASCADE)
    rating = models.FloatField(default=0.0, validators=[validate_rating_level])
    comment = models.TextField()

    def __str__(self):
        return self.passenger.__str__()

    def save(self, *args, **kwargs):
        created = not self.id
        super().save(*args, **kwargs)
        if created:
            self.passenger.booking.update_ratings()
            self.passenger.booking.save()

    class Meta:
        verbose_name = 'Transportation review'


@receiver(post_delete, sender=Driver)
def delete_driver_user(sender, instance, **kwargs):
    """Delete the driver user and driver images"""
    instance.user.delete()

    dir_path = None

    if instance.licence:
        dir_parts = PurePath(instance.licence.path).parts[:-2]
        dir_path = PurePath('').joinpath(*dir_parts)
    elif instance.id_card:
        dir_parts = PurePath(instance.id_card.path).parts[:-2]
        dir_path = PurePath('').joinpath(*dir_parts)

    if dir_path is not None:
        shutil.rmtree(dir_path, ignore_errors=True)


@receiver(post_delete, sender=Vehicle)
def delete_vehicle_files(sender, instance: Type[Vehicle], **kwargs):
    if instance.proof_of_ownership:
        try:
            os.remove(instance.proof_of_ownership.path)
        except Exception:
            pass


@receiver(post_delete, sender=TripPlan)
def delete_unbooked_trips(sender, instance: Type[TripPlan], **kwargs):
    """
    Delete trips that have not started yet when
    trip planning is deleted
    """
    trips = instance.get_trip_objects()
    for trip in trips:
        if not trip.has_started():
            trip.delete()
