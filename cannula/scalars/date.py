import datetime
import logging

from ._base import ScalarType

LOG = logging.getLogger(__name__)

try:
    from dateutil.parser import parse
except ImportError:  # pragma: no cover
    LOG.warning("dateutil library not installed, the date scalars will be degraded")

    def parse(  # type: ignore
        timestr: str,
    ) -> datetime.datetime:
        return datetime.datetime.strptime(timestr, "%Y-%m-%dT%H:%M:%S.%f")


class Date(ScalarType[datetime.date, str]):
    """Date seralizes to datetime.date objects"""

    @staticmethod
    def serialize(value: datetime.date) -> str:
        return value.isoformat()

    @staticmethod
    def parse_value(value: str) -> datetime.date:
        return parse(value).date()


class Datetime(ScalarType[datetime.datetime, str]):
    """Datetime seralizes to datetime.datetime objects"""

    @staticmethod
    def serialize(value: datetime.datetime) -> str:
        return value.isoformat()

    @staticmethod
    def parse_value(value: str) -> datetime.datetime:
        return parse(value)


class Time(ScalarType[datetime.time, str]):
    """Time seralizes to datetime.time objects"""

    @staticmethod
    def serialize(value: datetime.time) -> str:
        return value.isoformat()

    @staticmethod
    def parse_value(value: str) -> datetime.time:
        return parse(value).time()
