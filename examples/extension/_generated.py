from __future__ import annotations
import abc
import cannula
from abc import ABC
from dataclasses import dataclass
from typing import Awaitable, List, Optional, Protocol, Union
from typing_extensions import NotRequired, TypedDict


@dataclass(kw_only=True)
class BookTypeBase(ABC):
    __typename = "Book"
    name: Optional[str] = None
    author: Optional[str] = None

    @abc.abstractmethod
    def movies(self, info: cannula.ResolveInfo) -> Awaitable[Optional[List[MovieType]]]:
        pass


class BookTypeDict(TypedDict):
    movies: NotRequired[List[MovieType]]
    name: NotRequired[str]
    author: NotRequired[str]


BookType = Union[BookTypeBase, BookTypeDict]


@dataclass(kw_only=True)
class GenericThingTypeBase(ABC):
    __typename = "GenericThing"
    name: Optional[str] = None


class GenericThingTypeDict(TypedDict):
    name: NotRequired[str]


GenericThingType = Union[GenericThingTypeBase, GenericThingTypeDict]


@dataclass(kw_only=True)
class MovieTypeBase(ABC):
    __typename = "Movie"
    name: Optional[str] = None
    director: Optional[str] = None
    book: Optional[BookType] = None
    views: Optional[int] = None


class MovieTypeDict(TypedDict):
    name: NotRequired[str]
    director: NotRequired[str]
    book: NotRequired[BookType]
    views: NotRequired[int]


MovieType = Union[MovieTypeBase, MovieTypeDict]


@dataclass(kw_only=True)
class MovieInputTypeBase(ABC):
    __typename = "MovieInput"
    name: Optional[str] = None
    director: Optional[str] = None
    limit: Optional[int] = 100


class MovieInputTypeDict(TypedDict):
    name: NotRequired[str]
    director: NotRequired[str]
    limit: NotRequired[int]


MovieInputType = Union[MovieInputTypeBase, MovieInputTypeDict]


class booksQuery(Protocol):
    def __call__(self, info: cannula.ResolveInfo) -> Awaitable[List[BookType]]: ...


class createMovieMutation(Protocol):
    def __call__(
        self, info: cannula.ResolveInfo, *, input: Optional[MovieInputType] = None
    ) -> Awaitable[MovieType]: ...


class genericQuery(Protocol):
    def __call__(
        self, info: cannula.ResolveInfo
    ) -> Awaitable[List[GenericThingType]]: ...


class moviesQuery(Protocol):
    def __call__(
        self, info: cannula.ResolveInfo, *, limit: Optional[int] = 100
    ) -> Awaitable[List[MovieType]]: ...


class RootType(TypedDict):
    books: NotRequired[booksQuery]
    createMovie: NotRequired[createMovieMutation]
    generic: NotRequired[genericQuery]
    movies: NotRequired[moviesQuery]
