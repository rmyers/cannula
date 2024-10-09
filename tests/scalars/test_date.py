import datetime

from cannula.scalars.date import Date, Datetime, Time


def test_datetime_serialize():
    dt = datetime.datetime(
        year=2024, month=10, day=3, hour=12, minute=34, microsecond=8292
    )
    actual = Datetime.serialize(dt)
    assert actual == "2024-10-03T12:34:00.008292"


def test_datetime_parse_value():
    actual = Datetime.parse_value("2024-01-3 13:23")
    assert actual == datetime.datetime(year=2024, month=1, day=3, hour=13, minute=23)


def test_date_serialize():
    dt = datetime.date(year=2024, month=10, day=3)
    actual = Date.serialize(dt)
    assert actual == "2024-10-03"


def test_date_parse_value():
    actual = Date.parse_value("2024-01-3")
    assert actual == datetime.date(year=2024, month=1, day=3)


def test_time_serialize():
    t = datetime.time(hour=12, minute=34, microsecond=8292)
    actual = Time.serialize(t)
    assert actual == "12:34:00.008292"


def test_time_parse_value():
    actual = Time.parse_value("10:23 PM")
    assert actual == datetime.time(hour=22, minute=23)
