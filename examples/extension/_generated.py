from __future__ import annotations
from abc import ABC, abstractmethod
from cannula import ResolveInfo
from dataclasses import dataclass
from typing import Any, Optional, Protocol, Sequence
from typing_extensions import TypedDict

DatetimeType = Any


class GenericType(Protocol):
    name: Optional[str] = None


@dataclass(kw_only=True)
class BookType(ABC):
    __typename = "Book"
    name: Optional[str] = None
    author: Optional[str] = None

    @abstractmethod
    async def movies(
        self, info: ResolveInfo, *, limit: Optional[int] = 100
    ) -> Optional[Sequence[MovieType]]:
        """
        Get all the movies for a given book. This is will be added to the BookType.
        """
        ...


@dataclass(kw_only=True)
class MovieType(ABC):
    """
    Movie Type

    Includes a book reference defined in other schema file.
    """

    __typename = "Movie"
    name: Optional[str] = None
    director: Optional[str] = None
    book: Optional[BookType] = None
    views: Optional[int] = None
    created: Optional[DatetimeType] = None


class booksQuery(Protocol):

    async def __call__(self, info: ResolveInfo) -> Optional[Sequence[BookType]]: ...


class mediaQuery(Protocol):

    async def __call__(
        self, info: ResolveInfo, *, limit: Optional[int] = 100
    ) -> Optional[Sequence[GenericType]]: ...


class movieQuery(Protocol):

    async def __call__(self, info: ResolveInfo, name: str) -> Optional[MovieType]: ...


class RootType(TypedDict, total=False):
    books: Optional[booksQuery]
    media: Optional[mediaQuery]
    movie: Optional[movieQuery]
