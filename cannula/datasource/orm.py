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

from sqlalchemy import BinaryExpression, ColumnExpressionArgument, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase


from cannula.datasource import GraphModel, cacheable, expected_fields


DBModel = TypeVar("DBModel", bound=DeclarativeBase)
_PKIdentityArgument = Union[Any, Tuple[Any, ...]]

LOG = logging.getLogger(__name__)


class DatabaseRepository(Generic[DBModel, GraphModel]):
    """Repository for performing database queries."""

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
        async with self.session_maker() as session:
            instance = self._db_model(**data)
            session.add(instance)
            await session.commit()
            await session.refresh(instance)
            return self.from_db(instance)

    async def get_by_pk(self, pk: _PKIdentityArgument) -> DBModel | None:
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

    async def get_by_query(
        self, *expressions: BinaryExpression | ColumnExpressionArgument
    ) -> DBModel | None:
        query = select(self._db_model).where(*expressions)

        # Get the query as a string with bound values
        cache_key = str(query.compile(compile_kwargs={"literal_binds": True}))

        @cacheable
        async def process_get() -> DBModel | None:
            async with self.readonly_session_maker() as session:
                results = await session.scalars(query)
                return results.one_or_none()

        if results := self._memoized_get.get(cache_key):
            LOG.debug(f"Found cached query for {self.__class__.__name__}")
            return await results

        self._memoized_get[cache_key] = process_get()
        return await self._memoized_get[cache_key]

    async def get_model(self, pk: _PKIdentityArgument) -> GraphModel | None:
        if db_obj := await self.get_by_pk(pk):
            return self.from_db(db_obj)
        return None

    async def get_model_by_query(
        self, *expressions: BinaryExpression | ColumnExpressionArgument
    ) -> GraphModel | None:
        if db_obj := await self.get_by_query(*expressions):
            return self.from_db(db_obj)
        return None

    async def filter(
        self,
        *expressions: BinaryExpression | ColumnExpressionArgument,
        limit: int = 100,
        offset: int = 0,
    ) -> list[DBModel]:
        query = select(self._db_model).limit(limit).offset(offset)
        if expressions:
            query = query.where(*expressions)

        # Get the query as a string with bound values
        cache_key = str(query.compile(compile_kwargs={"literal_binds": True}))

        @cacheable
        async def process_filter() -> list[DBModel]:
            async with self.readonly_session_maker() as session:
                # If we don't convert this to a list only the first
                # coroutine that awaits this will be able to read the data.
                return list(await session.scalars(query))

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
    ) -> list[GraphModel]:
        return list(
            map(
                self.from_db,
                await self.filter(*expressions, limit=limit, offset=offset),
            )
        )
