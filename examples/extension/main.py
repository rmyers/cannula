import logging
import pathlib
import pprint

import cannula
import cannula.middleware
from ._generated import BookType, BookTypeBase, MovieType, RootType

BASE_DIR = pathlib.Path(__file__).parent


logging.basicConfig(level=logging.DEBUG)
LOG = logging.getLogger("expanded")


class Book(BookTypeBase):
    async def movies(self, info: cannula.ResolveInfo) -> list[MovieType]:
        LOG.info(f"{self.name}")
        return [{"name": "Lost the Movie", "director": "Ted"}]


async def get_books(info: cannula.ResolveInfo) -> list[BookType]:
    return [Book(name="Lost", author="Frank")]


root_value: RootType = {"books": get_books}

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
    }
"""
)


if __name__ == "__main__":
    results = api.call_sync(QUERY, None)
    pprint.pprint(results.data)
