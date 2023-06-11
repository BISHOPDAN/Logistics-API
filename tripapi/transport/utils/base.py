# Functions needed for just transport features

import datetime
from django.conf import settings
from utils.base.constants import DAY, WEEKDAYS_COUNT
from utils.base.general import get_day_value


def get_next_day_date(begin: datetime.date, day: str):
    """Get's the nearest weekday `day`
    for the nearest `begin`"""
    for _ in range(7):
        if begin.weekday() != get_day_value(day):
            begin += DAY
        else:
            break
    return begin


def generate_next_everydays(begin: datetime.date, count: int):
    """
    Generate the dates for the next count days
    """
    for _ in range(count):
        yield begin
        begin += DAY


def generate_next_weekdays(start_date: datetime.date, count: int):
    """
    This used to generate next dates for a particulary weekday
    it just increase by 7 days until count is reduced to zero
    """
    INCREMENT = datetime.timedelta(days=WEEKDAYS_COUNT)
    while count >= 0:
        yield start_date
        start_date += INCREMENT
        count -= WEEKDAYS_COUNT


def generate_next_n_days(begin: datetime.date, recurring_value: str):
    """
    Generate the next dates depending on the recurring_value
    and max_trip_plan_days
    """
    n_days: int = settings.MAX_TRIP_PLANS_DAYS
    if recurring_value == settings.EVERYDAY:
        return generate_next_everydays(begin, n_days)
    else:
        start_date = get_next_day_date(begin, recurring_value)
        return generate_next_weekdays(start_date, n_days)
