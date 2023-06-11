
from calendar import (FRIDAY, MONDAY, SATURDAY, SUNDAY, THURSDAY, TUESDAY,
                      WEDNESDAY)
import datetime
from unittest import TestCase


DAY = datetime.timedelta(days=1)

TOMORROW = datetime.date.today() + datetime.timedelta(days=1)

WEEKDAYS_COUNT = 7

WEEKDAYS = {
    "monday": MONDAY,
    "tuesday": TUESDAY,
    "wednesday": WEDNESDAY,
    "thursday": THURSDAY,
    "friday": FRIDAY,
    "saturday": SATURDAY,
    "sunday": SUNDAY,
}


unit = TestCase()
