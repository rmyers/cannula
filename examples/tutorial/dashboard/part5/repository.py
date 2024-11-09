import asyncio
import logging
from re import A
import uuid
from dataclasses import fields
from typing import (
    Any,
    Awaitable,
    ClassVar,
    Dict,
    Generic,
    List,
    Optional,
    Protocol,
    TypeVar,
    TYPE_CHECKING,
    cast,
)

from cannula.context import ResolveInfo
from sqlalchemy import BinaryExpression, ColumnExpressionArgument, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from ..core.config import config
from ..core.database import User as DBUser, Quota as DBQuota
from ._generated import UserTypeBase, QuotaType, QuotaTypeBase

from cannula.datasource.http import cacheable

if TYPE_CHECKING:  # pragma: no cover
    from .context import Context


class DataclassInstance(Protocol):
    __dataclass_fields__: ClassVar[dict[str, Any]]


GraphModel = TypeVar("GraphModel")

LOG = logging.getLogger(__name__)


class DatabaseRepository(Generic[GraphModel]):
    """Repository for performing database queries."""

    _memoized_get: Dict[str, Awaitable[GraphModel | None]]
    _memoized_list: Dict[str, Awaitable[list[GraphModel]]]
    _dbmodel: type[DeclarativeBase]
    _graphmodel: type[GraphModel]

    def __init_subclass__(
        cls, *, dbmodel: type[DeclarativeBase], graphmodel: type[GraphModel]
    ) -> None:
        cls._dbmodel = dbmodel
        cls._graphmodel = graphmodel
        return super().__init_subclass__()

    def __init__(self, session_maker: async_sessionmaker[AsyncSession]) -> None:
        self.session_maker = session_maker
        self._memoized_get = {}
        self._memoized_list = {}

    def from_db(self, db_obj: DeclarativeBase, **kwargs) -> GraphModel:
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

    async def get(self, pk: uuid.UUID) -> GraphModel | None:
        cache_key = f"get:{pk}"

        @cacheable
        async def process_get():
            async with self.session_maker() as session:
                if db_obj := await session.get(self._dbmodel, pk):
                    return self.from_db(db_obj)

        if results := self._memoized_get.get(cache_key):
            LOG.error(f"Found cached query for {cache_key}")
            return await results

        self._memoized_get[cache_key] = process_get()
        return await self._memoized_get[cache_key]

    async def filter(
        self,
        *expressions: BinaryExpression | ColumnExpressionArgument,
    ) -> list[GraphModel]:
        query = select(self._dbmodel)
        if expressions:
            query = query.where(*expressions)

        # Get the query as a string with bound values
        cache_key = str(query.compile(compile_kwargs={"literal_binds": True}))

        @cacheable
        async def process_filter():
            async with self.session_maker() as session:
                return list(map(self.from_db, await session.scalars(query)))

        if results := self._memoized_list.get(cache_key):
            LOG.error(f"\nfound cached results for {self.__class__.__name__}\n")
            return await results

        LOG.error(f"Caching data for {self.__class__.__name__}")
        self._memoized_list[cache_key] = process_filter()
        return await self._memoized_list[cache_key]


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


class UserRepository(DatabaseRepository[User], dbmodel=DBUser, graphmodel=User):
    pass


class QuotaRepository(DatabaseRepository[Quota], dbmodel=DBQuota, graphmodel=Quota):

    async def get_quota_for_user(self, id: uuid.UUID) -> List[Quota]:
        return await self.filter(DBQuota.user_id == id)

    async def get_over_quota(self, id: uuid.UUID, resource: str) -> Quota | None:
        quotas = await self.filter(DBQuota.user_id == id)
        for q in quotas:
            if q.resource == resource:
                return q
