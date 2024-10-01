import logging
import pathlib
import pprint

import cannula
import cannula.middleware
from ._generated import (
    BookType,
    BookTypeBase,
    GenericType,
    MovieType,
    MovieTypeBase,
    RootType,
)

BASE_DIR = pathlib.Path(__file__).parent


logging.basicConfig(level=logging.DEBUG)
LOG = logging.getLogger("expanded")


class Book(BookTypeBase):
    async def movies(self, info: cannula.ResolveInfo) -> list[MovieType]:
        LOG.info(f"{self.name}")
        return [{"name": "Lost the Movie", "director": "Ted"}]


class Movie(MovieTypeBase):
    pass


async def get_books(info: cannula.ResolveInfo) -> list[BookType]:
    return [Book(name="Lost", author="Frank")]


async def get_media(
    info: cannula.ResolveInfo, limit: int | None = 100
) -> list[GenericType]:
    return [
        Book(name="the Best Movies", author="Jane"),
        Movie(name="the Best Books", director="Sally"),
    ]


root_value: RootType = {"books": get_books, "media": get_media}

api = cannula.API[RootType](
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
    results = api.call_sync(QUERY, None)
    pprint.pprint(results.data)
    pprint.pprint(results.errors)
