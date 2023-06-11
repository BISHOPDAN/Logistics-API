from datetime import date
from django.conf import settings

from rest_framework.serializers import ValidationError
from django.utils.translation import gettext_lazy as _

from utils.base.general import today


class ErrCode:
    old_date = 'old_date'
    invalid_day = 'invalid_day'
    not_active = 'not_active'
    not_verified = 'not_verified'
    too_much_passengers = 'too_much_passengers'


def validate_recurring_data(value: str):
    if value:
        if value == settings.EVERYDAY:
            return

        # Means contains other days
        list_of_valid_days = [
            'monday', 'tuesday',
            'wednesday', 'thursday',
            'friday', 'saturday', 'sunday']

        if value.lower() in list_of_valid_days:
            return

        raise ValidationError(
            detail=_('Must provide a option for recurring days'),
            code=ErrCode.invalid_day
        )


def validate_start_date(date: date):
    this_day = today()
    if this_day > date:
        raise ValidationError(
            detail=_("Date is too old, select a future or current date"),
            code=ErrCode.old_date)


def validate_passengers_count(passengers: int, seats: int):
    if passengers > seats:
        raise ValidationError(
            detail=_("Passengers count is greater than available seats"),
            code=ErrCode.too_much_passengers
        )


# def validate_recurring_days(recurring_day: str, start_date: date):
#     if start_date.weekday() != get_day_value(recurring_day):
#         raise ValidationError(
#             detail=_(f"The Start date weekday has to be the same has \
# recurring days selected, which is {recurring_day}"),
#             code=ErrCode.invalid_day)


def validate_active(value):
    name: str = value.__class__.__name__
    if value.active is False:
        raise ValidationError(
            detail=_(f"Selected {name} is not active, \
kindly select an active {name.lower()} or activate the selected one"),
            code=ErrCode.not_active
        )


def validate_verified(value):
    name: str = value.__class__.__name__
    if value.verified is False:
        raise ValidationError(
            detail=_(f"Selected {name} is not verified, \
kindly select a verified {name.lower()}"),
            code=ErrCode.not_verified
        )
