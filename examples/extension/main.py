import pathlib
import pprint
import logging

import cannula
import cannula.middleware

logging.basicConfig(level=logging.DEBUG)

BASE_DIR = pathlib.Path(__file__).parent

api = cannula.API(
    schema=pathlib.Path(BASE_DIR / "schema"),
    middleware=[
        cannula.middleware.DebugMiddleware(),
    ],
)


@api.resolver("Query", "books")
def get_books(parent, info):
    return [{"name": "Lost", "author": "Frank"}]


@api.resolver("Book", "movies")
def get_movies_for_book(book, info):
    return [{"name": "Lost the Movie", "director": "Ted"}]


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
