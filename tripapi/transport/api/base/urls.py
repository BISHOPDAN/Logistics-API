from django.urls import include, path
from utils.base.routers import CustomDefaultRouter, CustomRouterNoLookup

from . import views


app_name = 'transport'


router = CustomDefaultRouter()

router.register(
    r'transporters',
    views.TransporterViewSet,
    basename='transporter')

router.register(
    r'bookings',
    views.BookingViewSet,
    basename='booking')

router.register(
    r'passengers',
    views.PassengerViewSet,
    basename='passenger')


router.register(
    r'tripplaning',
    views.TripTemplateViewSet,
    basename='tripplaning')


router.register(
    r'trips',
    views.TripViewSet,
    basename='trip')

router.register(
    r'drivers',
    views.DriverViewSet,
    basename='driver')

router.register(
    r'vehicles',
    views.VehicleViewSet,
    basename='vehicle')


no_lookup_router = CustomRouterNoLookup()
no_lookup_router.register(
    r'transporter',
    views.AuthTransporterViewSet,
    basename='auth-transporter'
)


urlpatterns = [
    path('', include(router.urls)),
    path('', include(no_lookup_router.urls)),
    path(
        'basic-analysis/',
        views.TransporterDashboardBasicAnalysis.as_view(),
        name='transporter-basic-analysis')
]
