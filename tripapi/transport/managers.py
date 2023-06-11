import datetime
from typing import Dict, Type, TypeVar, overload

from django.contrib.postgres.search import (SearchQuery, SearchRank,
                                            SearchVector)
from django.db.models import Manager, QuerySet
from utils.base.crypto import hash_digest
from django.core.cache import cache as _cache
from django.conf import settings
from django.core.cache.backends.base import BaseCache
from django.db.models import Q
from utils.base.db import count_queries  # noqa


cache: Type[BaseCache] = _cache
_QS = TypeVar("_QS", bound=QuerySet)


class VehicleQueryset(QuerySet):
    def create(self, **kwargs):
        clean_data = self.model.format_init_data(kwargs)
        return super().create(**clean_data)


class VehicleManager(Manager):
    def get_queryset(self):
        return VehicleQueryset(self.model, using=self._db)

    def create(self, **kwargs):
        return self.get_queryset().create(**kwargs)


class TripQueryset(QuerySet):
    def get_pending(self):
        return self.filter(state='pending')

    def get_started(self):
        return self.filter(state='started')

    def get_completed(self):
        return self.filter(state='completed')

    def get_cancelled(self):
        return self.filter(state='cancelled')

    # @count_queries
    def find_trips(
        self, origin: str, destination: str,
        leave_date: datetime.date, passengers: int,
        min_take_off_time: datetime.time = None,
        max_take_off_time: datetime.time = None,
        max_amount: int = None, vehicle_type: str = None,
        preferences: Dict[str, bool] = None
    ) -> _QS:
        """
        Search trips in queryset with parameters

        :param origin: current position of traveller
        :type origin: str
        :param destination: destination of traveller
        :type destination: str
        :param leave_date: date of travelling
        :type leave_date: datetime.date
        :param passengers: available seats in vehicles
        :type passengers: int
        :param min_take_off_time: minimum time to leave on leave date
        , defaults to None
        :type min_take_off_time: datetime.time, optional
        :param max_take_off_time: maximum time to leave on leave date
        , defaults to None
        :type max_take_off_time: datetime.time, optional
        :param max_amount: maximum amount for trip price, defaults to None
        :type max_amount: int, optional
        :param vehicle_type: kind of vehicle, defaults to None
        :type vehicle_type: str, optional
        :param preferences: specifications for vehicle, defaults to None
        :type preferences: Dict[str, bool], optional
        :return: _description_
        :rtype: _QS
        """

        kwargs = locals()
        kwargs.pop("self")

        key = hash_digest(kwargs)
        value = cache.get(key)

        if value is not None:
            cache.add(
                key, value, settings.SEARCH_TRIPS_CACHE_TIME_IN_SECONDS)
            return value

        from_vector = SearchVector('origin')
        to_vector = SearchVector('destination')
        from_query = SearchQuery(origin)
        to_query = SearchQuery(destination)

        from_ranking = SearchRank(from_vector, from_query)
        to_ranking = SearchRank(to_vector, to_query)

        queryset = self\
            .select_related("transporter", "driver", "vehicle")\
            .annotate(from_rank=from_ranking)\
            .annotate(to_rank=to_ranking)\
            .order_by('-from_rank', '-to_rank')\
            .filter(Q(from_rank__gte=0.000001) & Q(to_rank__gte=0.000001))\

        queryset = queryset.filter(leave_date=leave_date)
        queryset = queryset.filter(available_seats__gte=passengers)

        if min_take_off_time is not None:
            queryset = queryset.filter(take_off_time__gte=min_take_off_time)

        if max_take_off_time is not None:
            queryset = queryset.filter(take_off_time__lte=max_take_off_time)

        if max_amount is not None:
            queryset = queryset.filter(amount__lte=max_amount)

        if vehicle_type is not None:
            queryset = queryset.filter(vehicle__kind=vehicle_type)

        if preferences is not None:
            for preference, value in preferences.items():
                queryobj = {
                    f"vehicle__specifications__{preference}": value}
                queryset = queryset.filter(**queryobj)

        cache.set(
            key, queryset, settings.SEARCH_TRIPS_CACHE_TIME_IN_SECONDS)

        return queryset


class TripManager(Manager):
    def get_queryset(self):
        return TripQueryset(self.model, using=self._db)

    def get_pending(self):
        return self.get_queryset().get_pending()

    def get_started(self):
        return self.get_queryset().get_started()

    def get_completed(self):
        return self.get_queryset().get_completed()

    def get_cancelled(self):
        return self.get_queryset().get_cancelled()

    @overload
    def find_trips(
        self: _QS, origin: str, destination: str,
        leave_date: datetime.date, passengers: int,
        min_take_off_time: datetime.time = None,
        max_take_off_time: datetime.time = None,
        max_amount: int = None, vehicle_type: str = None,
        preferences: Dict[str, bool] = None
    ) -> _QS:
        ...

    def find_trips(self, **kwargs):
        return self.get_queryset().find_trips(**kwargs)


class BookingQueryset(QuerySet):
    def get_unconfirmed_bookings(self):
        return self.filter(state='unconfirmed')

    def get_confirmed_bookings(self):
        return self.filter(state='confirmed')

    def get_cancelled_bookings(self):
        return self.filter(state='cancelled')


class BookingManager(Manager):
    def get_queryset(self):
        return BookingQueryset(self.model, using=self._db)

    def get_unconfirmed_bookings(self):
        return self.get_queryset().get_unconfirmed_bookings()

    def get_confirmed_bookings(self):
        return self.get_queryset().get_confirmed_bookings()

    def get_cancelled_bookings(self):
        return self.get_queryset().get_cancelled_bookings()
