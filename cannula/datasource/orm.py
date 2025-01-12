"""
.. _ormdatasource:

ORM Data Source
===============

This is useful for mapping SQLAlchemy ORM models to generated graph models.
It follows the `Repository Pattern` and assists with memoized queries to
allow your resolvers to run concurrently and return the same results for
identical queryies.

.. note:: This requires that you have SQLAlchemy installed and configured properly.
"""

import logging

from typing import (
    Any,
    Awaitable,
    Dict,
    Generic,
    TypeVar,
    Tuple,
    Union,
)

from sqlalchemy import BinaryExpression, ColumnExpressionArgument, Select, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase


from cannula.datasource import GraphModel, cacheable, expected_fields


DBModel = TypeVar("DBModel", bound=DeclarativeBase)
_PKIdentityArgument = Union[Any, Tuple[Any, ...]]

LOG = logging.getLogger(__name__)


class DatabaseRepository(Generic[DBModel, GraphModel]):
    """Repository pattern for performing database queries and returning hydrated models.

    This object is constructed with both the database model and a generated graph
    model from :doc:`codegen`. It provides a couple helper methods to memoize
    queries that are read only operations cutting down on duplicate SQL calls.

    This class has an `__init_subclass__` that simplifies construction and will
    raise errors if incorrect types are used or missing. Construct a new object::

        class UserRepo(
            DatabaseRepository[DBUser, User],  # Adds specific types for return values
            db_model=DBUser,  # The
            graph_model=User
        ):

            async def get_user(pk: uuid.UUID) -> User:
                return self.get_model(pk)

    Class Arguments:

    * `db_model`: The database ORM model to perform queries with.
    * `graph_model`: Subclass of a generated graph model

    Args:
        session_maker:
            Session maker object that is read/write.
        readonly_session_maker:
            Optional readonly session maker object for spliting queries to different nodes.
    """

    _memoized_get: Dict[str, Awaitable[DBModel | None]]
    _memoized_list: Dict[str, Awaitable[list[DBModel]]]
    _db_model: type[DBModel]
    _graph_model: type[GraphModel]
    _expected_fields: set[str]

    def __init_subclass__(
        cls, *, db_model: type[DBModel], graph_model: type[GraphModel]
    ) -> None:
        cls._db_model = db_model
        cls._graph_model = graph_model
        cls._expected_fields = expected_fields(graph_model)
        return super().__init_subclass__()

    def __init__(
        self,
        session_maker: async_sessionmaker[AsyncSession],
        readonly_session_maker: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        self.session_maker = session_maker
        self.readonly_session_maker = readonly_session_maker or session_maker
        self._memoized_get = {}
        self._memoized_list = {}

    def from_db(self, db_obj: DBModel, **kwargs) -> GraphModel:
        """Hook for returning a GraphModel instance from a DBModel."""
        model_kwargs = db_obj.__dict__.copy()
        model_kwargs.update(kwargs)
        cleaned_kwargs = {
            key: value
            for key, value in model_kwargs.items()
            if key in self._expected_fields
        }
        obj = self._graph_model(**cleaned_kwargs)
        return obj

    async def add(self, **data: Any) -> GraphModel:
        """Insert a new object in the database."""
        async with self.session_maker() as session:
            instance = self._db_model(**data)
            session.add(instance)
            await session.commit()
            await session.refresh(instance)
            return self.from_db(instance)

    async def get_by_pk(self, pk: _PKIdentityArgument) -> DBModel | None:
        """Get a single database ORM model by primary key.

        .. note::
            This is query is memoized and intended to be used internally
            but is available to chain other database operations like resolving
            related objects.
        """
        cache_key = f"get:{pk}"

        @cacheable
        async def process_get() -> DBModel | None:
            async with self.readonly_session_maker() as session:
                return await session.get(self._db_model, pk)

        if results := self._memoized_get.get(cache_key):
            LOG.debug(f"Found cached query for {cache_key}")
            return await results

        self._memoized_get[cache_key] = process_get()
        return await self._memoized_get[cache_key]

    def _get_cache_key(self, query: Select, **kwargs) -> str:
        """Return a cache key for the query using with bind params.

        Get the params for the query and add in any from bindparams specified
        In the relation like::

            query: 'project.type == :type'
        """
        compiled = query.compile()
        params = compiled.params
        params.update(kwargs)
        cache_key = f"{compiled}:{params}"
        return cache_key

    async def get_by_query(
        self, *expressions: BinaryExpression | ColumnExpressionArgument, **kwargs
    ) -> DBModel | None:
        query = select(self._db_model).where(*expressions)

        # Get the query as a string with bound values
        cache_key = self._get_cache_key(query, **kwargs)

        @cacheable
        async def process_get() -> DBModel | None:
            async with self.readonly_session_maker() as session:
                results = await session.scalars(query, params=kwargs)
                return results.one_or_none()

        if results := self._memoized_get.get(cache_key):
            LOG.debug(f"Found cached query for {self.__class__.__name__}")
            return await results

        self._memoized_get[cache_key] = process_get()
        return await self._memoized_get[cache_key]

    async def get_model_by_pk(self, pk: _PKIdentityArgument) -> GraphModel | None:
        if db_obj := await self.get_by_pk(pk):
            return self.from_db(db_obj)
        return None

    async def get_model(
        self, *expressions: BinaryExpression | ColumnExpressionArgument, **kwargs
    ) -> GraphModel | None:
        if db_obj := await self.get_by_query(*expressions, **kwargs):
            return self.from_db(db_obj)
        return None

    async def filter(
        self,
        *expressions: BinaryExpression | ColumnExpressionArgument,
        limit: int = 100,
        offset: int = 0,
        **kwargs,
    ) -> list[DBModel]:
        query = select(self._db_model).limit(limit).offset(offset)
        if expressions:
            query = query.where(*expressions)

        # Get the query as a string with bound values
        cache_key = self._get_cache_key(query, **kwargs)

        @cacheable
        async def process_filter() -> list[DBModel]:
            async with self.readonly_session_maker() as session:
                # If we don't convert this to a list only the first
                # coroutine that awaits this will be able to read the data.
                return list(await session.scalars(query, params=kwargs))

        if results := self._memoized_list.get(cache_key):
            LOG.debug(f"Found cached results for {self.__class__.__name__}")
            return await results

        self._memoized_list[cache_key] = process_filter()
        return await self._memoized_list[cache_key]

    async def get_models(
        self,
        *expressions: BinaryExpression | ColumnExpressionArgument,
        limit: int = 100,
        offset: int = 0,
        **kwargs,
    ) -> list[GraphModel]:
        return list(
            map(
                self.from_db,
                await self.filter(*expressions, limit=limit, offset=offset, **kwargs),
            )
        )
