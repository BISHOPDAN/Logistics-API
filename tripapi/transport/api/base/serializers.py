from typing import Type

from django.contrib.auth import get_user_model
from rest_framework import serializers
from transport.models import (Booking, Driver, Passenger, Transporter,
                              TripObject, TripPlan, Vehicle)
from transport.validators import (validate_active, validate_passengers_count,
                                  validate_verified)
from utils.base.logger import err_logger, logger  # noqa
from utils.base.validators import (validate_file_size, validate_phone,
                                   validate_special_char)

User = get_user_model()


class TransporterSerializer(
    serializers.ModelSerializer
):
    email = serializers.CharField(source="user.email", read_only=True)
    phone = serializers.CharField(source="user.profile.phone", read_only=True)
    address = serializers.CharField(
        source="user.profile.address", read_only=True)
    logo = serializers.ImageField(source="user.profile.image", read_only=True)

    class Meta:
        model = Transporter
        exclude = ('user', 'id')
        read_only_fields = ('slug_name', 'rating')

    def validate(self, attrs):
        if self.instance is None:
            try:
                self.context.get('request').user.transporter
                raise serializers.ValidationError(
                    'User already owns a transport account', 'invalid_user')
            except Transporter.DoesNotExist:
                pass
        return super().validate(attrs)


class TransporterUpdateProfile(
    serializers.Serializer
):
    """Serializer for updating transporter basic information"""
    name = serializers.CharField(
        max_length=100,
        validators=[validate_special_char])
    phone = serializers.CharField(
        max_length=20,
        validators=[validate_phone],
        source="user.profile.phone")
    address = serializers.CharField(
        max_length=200,
        source="user.profile.address")

    def validate(self, attrs):
        return super().validate(attrs)

    @property
    def model_class(self) -> Type[Transporter]:
        return self.instance.__class__

    def validate_name(self, value):
        exists = self.model_class.objects.filter(
            name__exact=value
        ).exclude(id=self.instance.id).exists()
        if exists:
            raise serializers.ValidationError(
                detail="Name is not available",
                code="not_unique"
            )
        return value

    def update(self, instance, validated_data: dict):
        instance.name = validated_data['name']
        instance.user.profile.phone = \
            validated_data['user']['profile']['phone']
        instance.user.profile.address = \
            validated_data['user']['profile']['address']
        instance.user.profile.save()
        instance.save()
        return instance


class TransporterUploadLogo(
    serializers.Serializer
):
    logo = serializers.ImageField(validators=[validate_file_size()])

    def save(self):
        self.instance.user.profile.image = self.validated_data.get('logo')
        self.instance.user.profile.save()
        return self.instance


class TransBaseSerializer(
    serializers.Serializer
):
    bookings_unconfirmed = serializers.IntegerField(read_only=True)
    trips_pending = serializers.IntegerField(read_only=True)
    bookings_cancelled = serializers.IntegerField(read_only=True)


class ValidateDriverVehicleMixin:
    def validate_driver(self, value):
        validate_active(value)
        validate_verified(value)
        return value

    def validate_vehicle(self, value):
        validate_active(value)
        validate_verified(value)
        return value


class TripTemplateSerializer(
    serializers.ModelSerializer, ValidateDriverVehicleMixin
):
    vehicle_name = serializers.CharField(
        help_text='Name of vechicle placed for trip',
        source='get_vehicle_name',
        read_only=True)
    driver_name = serializers.CharField(
        help_text='Name of driver placed for trip',
        source='get_driver_name',
        read_only=True)

    class Meta:
        model = TripPlan
        exclude = ('id', 'transporter')
        read_only_fields = ('tracking_code', 'created',)
        extra_kwargs = {
            'driver': {'write_only': True},
            'vehicle': {'write_only': True},
        }

    def validate(self, attrs):
        validated = super().validate(attrs)
        pre_booked_seats = validated.get('pre_booked_seats')
        vehicle = validated.get('vehicle')
        if pre_booked_seats and vehicle:
            try:
                validate_passengers_count(pre_booked_seats, vehicle.capacity)
            except serializers.ValidationError as e:
                raise serializers.ValidationError({
                    'pre_booked_seats': e
                }, code=e.get_codes()[0])
        return validated


class TripSerializer(
    serializers.ModelSerializer, ValidateDriverVehicleMixin
):
    vehicle_name = serializers.CharField(
        help_text='Name of vechicle placed for trip',
        source='get_vehicle_name',
        read_only=True)
    driver_name = serializers.CharField(
        help_text='Name of driver placed for trip',
        source='get_driver_name',
        read_only=True)
    transporter_name = serializers.CharField(
        help_text='Name of trip company',
        source='get_transporter_name',
        read_only=True)
    available_passengers = serializers.IntegerField(
        help_text='Amount of passengers on trip',
        source='available_seats',
        read_only=True)
    arrival_time = serializers.TimeField(
        help_text='Arrival time of trip',
        source='get_arrival_time',
        read_only=True)

    class Meta:
        model = TripObject
        exclude = ('id', 'transporter', "available_seats")
        read_only_fields = ('tracking_code', 'created',)


class BookingSerializer(
    serializers.ModelSerializer
):
    trip_id = serializers.CharField(
        help_text='Trip code for booked trip',
        source='trip.get_trip_id',
        read_only=True)
    origin = serializers.CharField(
        help_text='Origin of booked trip',
        source='trip.origin',
        read_only=True)
    destination = serializers.CharField(
        help_text='Destination of booked trip',
        source='trip.destination',
        read_only=True)
    date = serializers.CharField(
        help_text='Date when booking was placed',
        source='get_created_date',
        read_only=True)
    time = serializers.CharField(
        help_text='Time when booking was placed',
        source='get_created_time',
        read_only=True)
    vehicle = serializers.CharField(
        help_text='Name of vechicle placed for trip',
        source='trip.vehicle',
        read_only=True)
    driver = serializers.CharField(
        help_text='Name of driver placed for trip',
        source='trip.driver',
        read_only=True)
    fee = serializers.FloatField(
        help_text='Amount payed for trip',
        source='trip.amount',
        read_only=True)

    class Meta:
        model = Booking
        exclude = ('user', 'id')
        read_only_fields = ('tracking_code', 'created', 'trip')


class PassengerSerializer(
    serializers.ModelSerializer
):
    booking_id = serializers.CharField(
        help_text='Booking code for booked trip',
        read_only=True,
        source='booking.tracking_code')
    fullname = serializers.CharField(
        help_text='Passenger\'s full name',
        read_only=True,
        source='get_fullname')
    rating = serializers.CharField(
        help_text='Passenger rating for trip travelled')

    # TODO: Create update for review rating right here

    class Meta:
        model = Passenger
        exclude = ('id', 'booking')


class DriverSerializer(
    serializers.ModelSerializer
):
    first_name = serializers.CharField(
        help_text='Driver\'s first name',
        max_length=60,
        source='user.profile.first_name')
    last_name = serializers.CharField(
        help_text='Driver\'s last name',
        max_length=60,
        source='user.profile.last_name')
    email = serializers.EmailField(
        help_text="""Driver\'s email, this must be a valid email.
This is only required when creating
a new driver. Email can't be updated with PUT or PATCH,
it is discarded if passed. To update
driver emails use User update endpoints""",
        required=False,
        source='user.email')
    phone = serializers.CharField(
        help_text='Driver\'s phone number',
        max_length=20,
        source='user.profile.phone')
    address = serializers.CharField(
        help_text='Driver\'s full home address',
        max_length=200,
        source='user.profile.address')
    trips_added = serializers.IntegerField(
        help_text='Number of trips driver is added to',
        source="get_trips_added",
        read_only=True)

    class Meta:
        model = Driver
        exclude = ('user', 'active', 'transporter')

    def validate_email(self, value):
        if not self.instance:
            if not value:
                raise serializers.ValidationError(
                    'Must provide an Driver\'s email')
            if User.objects.filter(email=value).exists():
                raise serializers.ValidationError(
                    'Email not available')
        else:
            if value:
                raise serializers.ValidationError(
                    'Email should not be provided, it is redundant'
                )
        return value

    def create(self, validated_data: dict):
        user: Type[User] = User.objects.create_base_user(
            email=validated_data['user'].get('email')
        )
        profile = user.profile
        profile_fields = ['first_name', 'last_name', 'phone', 'address']
        for attr in profile_fields:
            setattr(
                profile, attr,
                validated_data['user']['profile'].get(attr, ''))
        profile.account_type = 'driver'
        profile.save()

        request = self.context.get('request')
        transporter = request.user.transporter
        data = {
            'user': user,
            'transporter': transporter,
            'licence': validated_data.get('licence'),
            'id_card': validated_data.get('id_card'),
            'send_mail_verification': validated_data.get(
                'send_mail_verification')
        }
        driver = Driver.objects.create(**data)
        return driver

    def update(self, instance: Driver, validated_data: dict):
        profile = instance.user.profile
        profile_fields = ['first_name', 'last_name', 'phone', 'address']
        for attr in profile_fields:
            value = validated_data['user']['profile'].get(attr)
            if value is not None:
                setattr(profile, attr, value)
        profile.save()

        driver_fields = ['licence', 'id_card']
        for attr in driver_fields:
            value = validated_data.get(attr)
            if value is not None:
                setattr(instance, attr, value)
        instance.save()
        return instance


class VehicleSerializer(
    serializers.ModelSerializer
):
    trips_booked = serializers.IntegerField(
        help_text='Number of trips booked with vehicle',
        read_only=True,
        source='get_trips_count')

    def get_fields(self):
        """
        Override serializer fields to add new
        fields for specifications
        """
        data = super().get_fields()
        for field in self.Meta.model.get_specification_fields():
            key = field['name']
            help_text = field['help_text']
            data[key] = serializers.BooleanField(
                required=False,
                help_text=help_text
            )
        return data

    class Meta:
        model = Vehicle
        exclude = ('transporter', 'specifications')
        extra_kwargs = {
            'proof_of_ownership': {
                'write_only': True}}


class ChoiceOptionSerializer(serializers.Serializer):
    name = serializers.CharField(read_only=True)
    value = serializers.CharField(read_only=True)


class ChoiceSerializer(serializers.Serializer):
    types = ChoiceOptionSerializer(many=True)


class SearchSerializer(serializers.Serializer):
    search = serializers.CharField(required=True)
