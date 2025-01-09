import logging
import pathlib
import pprint
from typing import Sequence

import cannula
import cannula.middleware
from .gql.types import (
    Book as BookType,
    Generic,
    Movie,
    RootType,
)

BASE_DIR = pathlib.Path(__file__).parent


logging.basicConfig(level=logging.DEBUG)
LOG = logging.getLogger("expanded")


class Book(BookType):
    async def movies(
        self, info: cannula.ResolveInfo, *, limit: int | None = 100
    ) -> list[Movie] | None:
        return [Movie(name="Lost the Movie", director="Ted")]


async def get_books(info: cannula.ResolveInfo) -> Sequence[Book]:
    return [Book(name="Lost", author="Frank")]


async def get_media(
    info: cannula.ResolveInfo, limit: int | None = 100
) -> list[Generic]:
    return [
        Book(name="the Best Movies", author="Jane"),
        Movie(name="the Best Books", director="Sally"),
    ]


root_value: RootType = {"books": get_books, "media": get_media}

api = cannula.CannulaAPI[RootType](
    root_value=root_value,
    schema=pathlib.Path(BASE_DIR / "schema"),
    middleware=[
        cannula.middleware.DebugMiddleware(),
    ],
)

QUERY = cannula.gql(
    """
    query BookList {
        books {
            name
            author
            movies {
                name
                director
            }
        }
        media {
            __typename
            name
            ... on Book {
                author
            }
            ... on Movie {
                director
            }
        }
    }
"""
)


if __name__ == "__main__":
    results = api.call_sync(QUERY)
    pprint.pprint(results.data)
    pprint.pprint(results.errors)
