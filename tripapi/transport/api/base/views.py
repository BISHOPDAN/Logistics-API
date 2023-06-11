from account.api.base.permissions import (
    AuthUserIsTransporter, BasicPerm,
    SuperPerm)
from transport.managers import TripQueryset
from django.utils.functional import cached_property
from drf_yasg.utils import swagger_auto_schema
from rest_framework import views, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from transport.models import (Booking, Driver, Passenger, Transporter,
                              TripObject, TripPlan, Vehicle)
from utils.base.general import choices_to_dict, regexify
from utils.base.logger import err_logger  # noqa
from utils.base.mixins import ListMixinUtils, UpdateRetrieveViewSet

from .serializers import (BookingSerializer, ChoiceSerializer,
                          DriverSerializer, PassengerSerializer,
                          SearchSerializer, TransBaseSerializer,
                          TransporterSerializer, TransporterUpdateProfile,
                          TransporterUploadLogo, TripSerializer,
                          TripTemplateSerializer, VehicleSerializer)


class TransporterViewSet(viewsets.ModelViewSet):
    """
    A viewset for creating, viewing and editing
    transport instances.
    """
    serializer_class = TransporterSerializer
    lookup_field = 'slug_name'
    permission_classes = (BasicPerm,)

    def get_queryset(self):
        return Transporter.objects.all().order_by('name')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class AuthTransporterViewSet(UpdateRetrieveViewSet):
    """
    A viewset for viewing and editing logged in
    transporters.
    """
    serializer_class = TransporterSerializer
    permission_classes = (AuthUserIsTransporter,)

    def get_queryset(self):
        return Transporter.objects.prefetch_related('user', 'user__profile')

    def get_object(self):
        return self.request.user.transporter

    @swagger_auto_schema(
        request_body=TransporterUpdateProfile,
        responses={
            '200': TransporterUpdateProfile
        }
    )
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = TransporterUpdateProfile(
            instance, data=request.data
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        # From rest framework main update mixin code
        if getattr(instance, '_prefetched_objects_cache', None):
            instance._prefetched_objects_cache = {}

        return Response(serializer.data)

    @swagger_auto_schema(
        request_body=TransporterUploadLogo,
        responses={
            '200': ''
        }
    )
    @action(detail=False, methods=['post'], url_path='upload/logo')
    def upload_logo(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = TransporterUploadLogo(
            instance, data=request.FILES
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response()


class TransporterDashboardBasicAnalysis(views.APIView):
    serializer_class = TransBaseSerializer
    permission_classes = (AuthUserIsTransporter,)

    def get(self, request, *args, **kwargs):
        trans = request.user.transporter
        data = {
            'bookings_unconfirmed': trans.get_unconfirmed_bookings().count(),
            'trips_pending': trans.get_pending_trips().count(),
            'bookings_cancelled': trans.get_cancelled_bookings().count(),
        }
        return Response(data)


class TripTemplateViewSet(viewsets.ModelViewSet):
    """
    A viewset for viewing and editing
    trip plans.
    """
    serializer_class = TripTemplateSerializer
    permission_classes = (AuthUserIsTransporter,)
    lookup_field = 'tracking_code'
    model = TripPlan

    @cached_property
    def transporter(self):
        return self.request.user.transporter

    def get_queryset(self):
        return self.model.objects.filter(
            transporter=self.transporter).order_by('-created')

    def perform_create(self, serializer):
        serializer.save(transporter=self.transporter)

    @swagger_auto_schema(
        responses={200: ChoiceSerializer}
    )
    @action(detail=False, methods=['get'], url_path='trip-types')
    def list_trip_types(self, request, *args, **kwargs):
        """List all trip types"""
        data = choices_to_dict(TripPlan.TRIP_TYPES)
        return Response(data)


class TripViewSet(ListMixinUtils, TripTemplateViewSet):
    """
    A viewset for viewing and editing
    trip instances.
    """
    serializer_class = TripSerializer
    model = TripObject

    def get_queryset(self) -> TripQueryset:
        return self.get_all_queryset().filter(
            transporter=self.transporter)

    def get_all_queryset(self) -> TripQueryset:
        return self.model.objects.select_related(
            "transporter", "vehicle", "driver").order_by('leave_date')

    def get_trips_filter(self, state: str):
        return self.filter_queryset(
            self.get_queryset()).filter(state=state)

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions
        that this view requires.
        """
        if self.action in ('search', 'all_trips'):
            permission_classes = (
                SuperPerm,)
        else:
            permission_classes = self.permission_classes
        return [permission() for permission in permission_classes]

    @action(
        detail=False, methods=['get'],
        url_path='all', url_name='all')
    def all_trips(self, request, *args, **kwargs):
        return self.get_with_queryset(self.get_all_queryset())

    @action(
        detail=False, methods=['get'],
        url_path='search', url_name='search')
    def search(self, request, *args, **kwargs):
        params = request.query_params.dict()
        fields = ("origin", "destination", "leave_date", "passengers")
        for key in fields:
            if key not in params:
                return Response(
                    f"Missing required query parameter {key}",
                    status=400
                )

        try:
            queryset = self.get_all_queryset().find_trips(**params)
        except TypeError:
            return Response(
                "Invalid query parameter",
                status=400
            )

        return self.get_with_queryset(queryset)

    @action(
        detail=False, methods=['get'],
        url_path='pending', url_name='pending')
    def pending_trips(self, request, *args, **kwargs):
        queryset = self.get_queryset().get_pending()
        return self.get_with_queryset(queryset)

    @action(
        detail=False, methods=['get'],
        url_path='cancelled', url_name='cancelled')
    def cancelled_trips(self, request, *args, **kwargs):
        queryset = self.get_queryset().get_cancelled()
        return self.get_with_queryset(queryset)

    @action(
        detail=False, methods=['get'],
        url_path='completed', url_name='completed')
    def completed_trips(self, request, *args, **kwargs):
        queryset = self.get_queryset().get_completed()
        return self.get_with_queryset(queryset)

    @action(
        detail=False, methods=['get'],
        url_path='started', url_name='started')
    def started_trips(self, request, *args, **kwargs):
        queryset = self.get_queryset().get_started()
        return self.get_with_queryset(queryset)


class BookingViewSet(ListMixinUtils, viewsets.ModelViewSet):
    """
    A viewset for viewing and editing booking instances for
    authenticated transporter.
    """
    serializer_class = BookingSerializer
    permission_classes = (AuthUserIsTransporter,)
    lookup_field = 'tracking_code'

    def get_queryset(self):
        return Booking.objects.filter(
            trip__transporter=self.request.user.transporter
        ).order_by('-created')

    def get_bookings_filter(self, state: str):
        return self.filter_queryset(
            self.get_queryset()).filter(state=state)

    @action(detail=False, methods=['get'], url_path='history/confirmed')
    def confirmed_bookings(self, request, *args, **kwargs):
        queryset = self.get_bookings_filter('confirmed')
        return self.get_with_queryset(queryset)

    @action(detail=False, methods=['get'], url_path='history/unconfirmed')
    def unconfirmed_bookings(self, request, *args, **kwargs):
        queryset = self.get_bookings_filter('unconfirmed')
        return self.get_with_queryset(queryset)

    @action(detail=False, methods=['get'], url_path='history/cancelled')
    def cancelled_bookings(self, request, *args, **kwargs):
        queryset = self.get_bookings_filter('cancelled')
        return self.get_with_queryset(queryset)


class PassengerViewSet(viewsets.ModelViewSet):
    """
    A viewset for viewing and editing passenger instances.
    """
    serializer_class = PassengerSerializer
    permission_classes = (AuthUserIsTransporter,)
    lookup_field = 'tracking_code'

    def get_queryset(self):
        return Passenger.objects.filter(
            booking__trip__transporter=self.request.user.transporter
        ).order_by('id')


class DriverViewSet(ListMixinUtils, viewsets.ModelViewSet):
    """
    A viewset for viewing and editing driver instances.
    """
    serializer_class = DriverSerializer
    permission_classes = (AuthUserIsTransporter,)
    lookup_field = 'tracking_code'

    def get_queryset(self):
        return Driver.objects.filter(
            transporter=self.request.user.transporter).prefetch_related(
                'user', 'user__profile').order_by('-id')

    @swagger_auto_schema(
        query_serializer=SearchSerializer
    )
    @action(detail=False, methods=['get'], url_path='search')
    def search_drivers(self, request, *args, **kwargs):
        """Search drivers by phone number and email"""
        search = request.query_params.get('search', None)
        if search is None:
            return Response(
                {'error': 'Please provide a search parameter'},
                status=400)
        drivers = (self.get_queryset().filter(
            user__profile__phone__icontains=search
        ) | self.get_queryset().filter(
            user__email__icontains=search
        )).distinct()
        return self.get_with_queryset(drivers)

    @action(detail=False, methods=['get'], url_path='verified')
    def verified(self, request, *args, **kwargs):
        """Get verified and active instances"""
        queryset = self.get_queryset().filter(
            verified=True).filter(active=True)
        return self.get_with_queryset(queryset)


class VehicleViewSet(ListMixinUtils, viewsets.ModelViewSet):
    """
    A viewset for viewing and editing vehicle instances.
    """
    serializer_class = VehicleSerializer
    permission_classes = (AuthUserIsTransporter,)
    lookup_field = 'tag'

    def get_queryset(self):
        """Get all vehicles for the logged in transporter."""
        return Vehicle.objects.filter(
            transporter=self.request.user.transporter).order_by('id')

    def perform_create(self, serializer):
        serializer.save(transporter=self.request.user.transporter)

    @swagger_auto_schema(
        query_serializer=SearchSerializer
    )
    @action(detail=False, methods=['get'], url_path='search')
    def search_vehicles(self, request, *args, **kwargs):
        """Search vehicles by plate number"""
        search = request.query_params.get('search', None)
        if search is None:
            return Response(
                {'error': 'Please provide a search parameter'},
                status=400)
        vehicles = self.get_queryset().filter(
            plate_number__icontains=search
        )
        return self.get_with_queryset(vehicles)

    @swagger_auto_schema(
        responses={200: ChoiceSerializer}
    )
    @action(detail=False, methods=['get'], url_path='list-types')
    def list_types(self, request, *args, **kwargs):
        """List all vehicle types"""
        data = choices_to_dict(Vehicle.VEHICLE_TYPE)
        return Response(data)

    @action(
        detail=False, methods=['delete'],
        url_path=f"delete/all/{regexify('tags')}"
    )
    def delete_all(self, request, *args, **kwargs):
        """Delete all vehicles with given tags"""
        tags = self.kwargs.get('tags')
        if tags is None:
            return Response(
                {'error': 'Please provide a tag parameter'},
                status=400)
        tags = [tag for tag in tags.split(',') if tag]
        self.get_queryset().filter(tag__in=tags).delete()
        return Response(status=204)

    @action(detail=False, methods=['get'], url_path='verified')
    def verified(self, request, *args, **kwargs):
        """Get verified and active instances"""
        queryset = self.get_queryset().filter(
            verified=True).filter(active=True)
        return self.get_with_queryset(queryset)
