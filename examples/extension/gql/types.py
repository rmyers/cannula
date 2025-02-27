from __future__ import annotations
from abc import ABC
from cannula import ResolveInfo
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Protocol, Sequence, TYPE_CHECKING
from typing_extensions import TypedDict

if TYPE_CHECKING:
    from .context import Context


class Generic(Protocol):
    name: str


@dataclass(kw_only=True)
class Book(ABC):
    """books are cool"""

    __typename = "Book"
    name: str
    author: Optional[str] = None

    async def movies(
        self, info: ResolveInfo["Context"], *, limit: int = 100
    ) -> Optional[Sequence[Movie]]:
        """Get all the movies for a given book. This is will be added to the BookType."""
        return await info.context.movies.book_movies(limit=limit)


@dataclass(kw_only=True)
class Movie(ABC):
    """
    Movie Type

    Includes a book reference defined in other schema file.
    """

    __typename = "Movie"
    name: str
    director: Optional[str] = None
    views: Optional[int] = None
    created: Optional[datetime] = None

    async def book(self, info: ResolveInfo["Context"]) -> Optional[Book]:
        return await info.context.books.movie_book(name=self.name)


class booksQuery(Protocol):

    async def __call__(
        self, info: ResolveInfo["Context"]
    ) -> Optional[Sequence[Book]]: ...


class mediaQuery(Protocol):

    async def __call__(
        self, info: ResolveInfo["Context"], *, limit: int = 100
    ) -> Optional[Sequence[Generic]]: ...


class movieQuery(Protocol):

    async def __call__(
        self, info: ResolveInfo["Context"], name: str
    ) -> Optional[Movie]: ...


class RootType(TypedDict, total=False):
    books: Optional[booksQuery]
    media: Optional[mediaQuery]
    movie: Optional[movieQuery]
