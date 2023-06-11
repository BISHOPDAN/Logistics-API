from django.contrib import admin

from .models import (Booking, Driver, Passenger, Review, Transporter,
                     TripObject, TripPlan, Vehicle)

admin.site.register((
    Driver, Transporter, Booking,
    Passenger, Vehicle, Review, TripObject, TripPlan))
