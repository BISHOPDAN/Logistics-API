import datetime

import pytest
from transport.utils.base import (generate_next_everydays,
                                  generate_next_n_days, get_next_day_date)


def test_generate_next_n_days(settings):
    settings.MAX_TRIP_PLANS_DAYS = 30
    begin = datetime.date(2022, 8, 12)
    weekday = 'friday'
    expected = [
        datetime.date(2022, 8, 12),
        datetime.date(2022, 8, 19),
        datetime.date(2022, 8, 26),
        datetime.date(2022, 9, 2),
        datetime.date(2022, 9, 9),
    ]
    gen = generate_next_n_days(begin, weekday)
    for expect in expected:
        computed = next(gen)
        assert computed == expect


@pytest.mark.parametrize(
    "begin, count",
    [
        (datetime.date(2022, 8, 1), 40),
        (datetime.date(2022, 8, 11), 20),
        (datetime.date(2022, 9, 1), 10),
        (datetime.date(2025, 1, 5), 60),
    ]
)
def test_generate_next_everydays(begin, count):
    gen = list(generate_next_everydays(begin, count))
    assert len(gen) == count


@pytest.mark.parametrize(
    "begin, day, expected",
    [
        ((2022, 8, 12), 'friday', (2022, 8, 12)),
        ((2022, 8, 12), 'monday', (2022, 8, 15)),
        ((2022, 8, 16), 'friday', (2022, 8, 19)),
        ((2022, 3, 12), 'sunday', (2022, 3, 13)),
        ((2022, 9, 5), 'thursday', (2022, 9, 8)),
        ((2022, 10, 10), 'wednesday', (2022, 10, 12)),
    ]
)
def test_get_next_day_date(begin, day, expected):
    start = datetime.date(*begin)
    expected_date = datetime.date(*expected)
    assert expected_date == get_next_day_date(start, day)
