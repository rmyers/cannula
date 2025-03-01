from __future__ import annotations
from cannula.context import Context as BaseContext
from cannula.datasource.orm import DatabaseRepository
from sqlalchemy import text, true
from sqlalchemy.ext.asyncio import async_sessionmaker
from typing import Optional, Protocol, Sequence
from .sql import DBBook, DBMovie
from .types import Book, Movie


class BookDatasource(
    DatabaseRepository[DBBook, Book], graph_model=Book, db_model=DBBook
):

    async def movie_book(self, name: str) -> Optional[Book]:
        return await self.get_model(text("name = :name").bindparams(name=name))

    async def query_books(self) -> Optional[Sequence[Book]]:
        return await self.get_models(true())


class MovieDatasource(
    DatabaseRepository[DBMovie, Movie], graph_model=Movie, db_model=DBMovie
):

    async def book_movies(self, *, limit: int = 100) -> Optional[Sequence[Movie]]:
        return await self.get_models(true())

    async def query_movie(self, name: str) -> Optional[Movie]:
        return await self.get_model(text("name = :name").bindparams(name=name))


class Settings(Protocol):

    @property
    def session(self) -> async_sessionmaker: ...

    @property
    def readonly_session(self) -> Optional[async_sessionmaker]: ...


class Context(BaseContext[Settings]):
    books: BookDatasource
    movies: MovieDatasource

    def init(self):
        self.books = BookDatasource(self.config.session)
        self.movies = MovieDatasource(self.config.session)
