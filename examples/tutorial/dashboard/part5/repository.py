import logging

import uuid
from dataclasses import fields
from typing import (
    Any,
    Awaitable,
    ClassVar,
    Dict,
    Generic,
    List,
    Protocol,
    TypeVar,
    TYPE_CHECKING,
    cast,
)

from cannula.context import ResolveInfo
from sqlalchemy import BinaryExpression, ColumnExpressionArgument, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from ..core.database import User as DBUser, Quota as DBQuota
from ._generated import UserTypeBase, QuotaTypeBase

from cannula.datasource.http import cacheable

if TYPE_CHECKING:  # pragma: no cover
    from .context import Context


class DataclassInstance(Protocol):
    __dataclass_fields__: ClassVar[dict[str, Any]]


GraphModel = TypeVar("GraphModel")
DBModel = TypeVar("DBModel", bound=DeclarativeBase)

LOG = logging.getLogger(__name__)


class DatabaseRepository(Generic[DBModel, GraphModel]):
    """Repository for performing database queries."""

    _memoized_get: Dict[str, Awaitable[DBModel | None]]
    _memoized_list: Dict[str, Awaitable[list[DBModel]]]
    _dbmodel: type[DBModel]
    _graphmodel: type[GraphModel]

    def __init_subclass__(
        cls, *, dbmodel: type[DBModel], graphmodel: type[GraphModel]
    ) -> None:
        cls._dbmodel = dbmodel
        cls._graphmodel = graphmodel
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
        expected_fields = {
            field.name for field in fields(cast(DataclassInstance, self._graphmodel))
        }
        cleaned_kwargs = {
            key: value for key, value in model_kwargs.items() if key in expected_fields
        }
        obj = self._graphmodel(**cleaned_kwargs)
        return obj

    async def add(self, **data: Any) -> GraphModel:
        async with self.session_maker() as session:
            instance = self._dbmodel(**data)
            session.add(instance)
            await session.commit()
            await session.refresh(instance)
            return self.from_db(instance)

    async def get_by_pk(self, pk: uuid.UUID) -> DBModel | None:
        cache_key = f"get:{pk}"

        @cacheable
        async def process_get():
            async with self.readonly_session_maker() as session:
                return await session.get(self._dbmodel, pk)

        if results := self._memoized_get.get(cache_key):
            LOG.error(f"Found cached query for {cache_key}")
            return await results

        self._memoized_get[cache_key] = process_get()
        return await self._memoized_get[cache_key]

    async def get_by_query(
        self, *expressions: BinaryExpression | ColumnExpressionArgument
    ) -> DBModel | None:
        query = select(self._dbmodel).where(*expressions)

        # Get the query as a string with bound values
        cache_key = str(query.compile(compile_kwargs={"literal_binds": True}))

        @cacheable
        async def process_get():
            async with self.readonly_session_maker() as session:
                results = await session.scalars(query)
                return results.one_or_none()

        if results := self._memoized_get.get(cache_key):
            LOG.error(f"Found cached query for {cache_key}")
            return await results

        self._memoized_get[cache_key] = process_get()
        return await self._memoized_get[cache_key]

    async def get(self, pk: uuid.UUID) -> GraphModel | None:
        if db_obj := await self.get_by_pk(pk):
            return self.from_db(db_obj)

    async def get_by(
        self, *expressions: BinaryExpression | ColumnExpressionArgument
    ) -> GraphModel | None:
        if db_obj := await self.get_by_query(*expressions):
            return self.from_db(db_obj)

    async def query_db(
        self,
        *expressions: BinaryExpression | ColumnExpressionArgument,
        limit: int = 100,
        offset: int = 0,
    ) -> list[DBModel]:
        query = select(self._dbmodel).limit(limit).offset(offset)
        if expressions:
            query = query.where(*expressions)

        # Get the query as a string with bound values
        cache_key = str(query.compile(compile_kwargs={"literal_binds": True}))

        @cacheable
        async def process_filter():
            async with self.readonly_session_maker() as session:
                # If we don't convert this to a list only the first
                # coroutine that awaits this will be able to read the data.
                return list(await session.scalars(query))

        if results := self._memoized_list.get(cache_key):
            LOG.error(cache_key)
            LOG.error(f"\nfound cached results for {self.__class__.__name__}\n")
            return await results

        LOG.error(f"Caching data for {self.__class__.__name__}")
        self._memoized_list[cache_key] = process_filter()
        return await self._memoized_list[cache_key]

    async def filter(
        self,
        *expressions: BinaryExpression | ColumnExpressionArgument,
        limit: int = 100,
        offset: int = 0,
    ) -> list[GraphModel]:
        return list(
            map(
                self.from_db,
                await self.query_db(*expressions, limit=limit, offset=offset),
            )
        )


class User(UserTypeBase):
    """User instance"""

    async def quota(self, info: ResolveInfo["Context"]) -> List["Quota"] | None:
        return await info.context.quota_repo.get_quota_for_user(self.id)

    async def overQuota(
        self, info: ResolveInfo["Context"], *, resource: str
    ) -> "Quota | None":
        return await info.context.quota_repo.get_over_quota(self.id, resource=resource)


class Quota(QuotaTypeBase):
    pass


class UserRepository(
    DatabaseRepository[DBUser, User],
    dbmodel=DBUser,
    graphmodel=User,
):
    pass


class QuotaRepository(
    DatabaseRepository[DBQuota, Quota],
    dbmodel=DBQuota,
    graphmodel=Quota,
):

    async def get_quota_for_user(self, id: uuid.UUID) -> List[Quota]:
        return await self.filter(DBQuota.user_id == id)

    async def get_over_quota(self, id: uuid.UUID, resource: str) -> Quota | None:
        return await self.get_by(DBQuota.user_id == id, DBQuota.resource == resource)
