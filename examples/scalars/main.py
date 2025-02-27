import datetime
import logging
import pathlib
import pprint
import typing
import uuid

import cannula
from cannula.scalars.date import Date, Datetime, Time
from cannula.scalars.util import JSON, UUID

from .gql.types import (
    Scaled,
    RootType,
)

BASE_DIR = pathlib.Path(__file__).parent


logging.basicConfig(level=logging.DEBUG)
LOG = logging.getLogger("scalars")

uid = uuid.UUID("e0c2c649-9c66-4f55-a2d4-966cc4f7d186")


async def get_scaled(info: cannula.ResolveInfo) -> Scaled:
    return Scaled(
        id=uid,
        created=datetime.datetime(year=2024, month=2, day=5, hour=6, minute=47),
        birthday=datetime.date(year=2019, month=3, day=8),
        smoke=datetime.time(hour=4, minute=20),
        meta={"fancy": "pants"},
    )


api = cannula.CannulaAPI[RootType, typing.Any](
    root_value={"scaled": get_scaled},
    schema=pathlib.Path(BASE_DIR),
    scalars=[
        Date,
        Datetime,
        Time,
        JSON,
        UUID,
    ],
)

QUERY = cannula.gql(
    """
    query Scaled {
        scaled {
            id
            created
            birthday
            smoke
            meta
        }
    }
"""
)


if __name__ == "__main__":
    results = api.call_sync(QUERY)
    pprint.pprint(results.data)
    pprint.pprint(results.errors)
