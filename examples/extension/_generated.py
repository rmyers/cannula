from __future__ import annotations
from abc import ABC, abstractmethod
from cannula import ResolveInfo
from dataclasses import dataclass
from typing import Any, List, Optional, Protocol, Union
from typing_extensions import TypedDict

DatetimeType = Any


class GenericType(Protocol):
    __typename = "Generic"
    name: Optional[str] = None


@dataclass(kw_only=True)
class BookTypeBase(ABC):
    __typename = "Book"
    name: Optional[str] = None
    author: Optional[str] = None

    @abstractmethod
    async def movies(
        self, info: ResolveInfo, *, limit: Optional[int] = 100
    ) -> Optional[List[MovieType]]:
        """
        Get all the movies for a given book. This is will be added to the BookType."""
        ...


class BookTypeDict(TypedDict, total=False):
    movies: Optional[List[MovieType]]
    name: Optional[str]
    author: Optional[str]


BookType = Union[BookTypeBase, BookTypeDict]


@dataclass(kw_only=True)
class MovieTypeBase(ABC):
    """
    Movie Type

    Includes a book reference defined in other schema file."""

    __typename = "Movie"
    name: Optional[str] = None
    director: Optional[str] = None
    book: Optional[BookType] = None
    views: Optional[int] = None
    created: Optional[DatetimeType] = None


class MovieTypeDict(TypedDict, total=False):
    name: Optional[str]
    director: Optional[str]
    book: Optional[BookType]
    views: Optional[int]
    created: Optional[DatetimeType]


MovieType = Union[MovieTypeBase, MovieTypeDict]


class booksQuery(Protocol):
    async def __call__(self, info: ResolveInfo) -> List[BookType]:
        ...


class mediaQuery(Protocol):
    async def __call__(
        self, info: ResolveInfo, *, limit: Optional[int] = 100
    ) -> List[GenericType]:
        ...


class RootType(TypedDict, total=False):
    books: Optional[booksQuery]
    media: Optional[mediaQuery]
