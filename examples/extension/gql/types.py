from __future__ import annotations
from abc import ABC, abstractmethod
from cannula import ResolveInfo
from dataclasses import dataclass
from typing import Any, Optional, Protocol, Sequence, TYPE_CHECKING
from typing_extensions import TypedDict

if TYPE_CHECKING:
    from .context import Context


class Generic(Protocol):
    name: Optional[str] = None


@dataclass(kw_only=True)
class Book(ABC):
    """books are cool"""

    __typename = "Book"
    name: Optional[str] = None
    author: Optional[str] = None

    @abstractmethod
    async def movies(
        self, info: ResolveInfo["Context"], *, limit: int = 100
    ) -> Optional[Sequence[Movie]]:
        """Get all the movies for a given book. This is will be added to the BookType."""
        ...


@dataclass(kw_only=True)
class Movie(ABC):
    """
    Movie Type

    Includes a book reference defined in other schema file.
    """

    __typename = "Movie"
    name: Optional[str] = None
    director: Optional[str] = None
    book: Optional[Book] = None
    views: Optional[int] = None
    created: Optional[Any] = None


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
