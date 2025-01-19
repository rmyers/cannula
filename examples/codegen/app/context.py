from __future__ import annotations
from cannula.context import Context as BaseContext
from cannula.datasource.orm import DatabaseRepository
from sqlalchemy import text, true
from sqlalchemy.ext.asyncio import async_sessionmaker
from typing import Optional, Sequence
from uuid import UUID
from .sql import DBQuota, DBUser
from .types import Quota, User


class QuotaDatasource(
    DatabaseRepository[DBQuota, Quota], graph_model=Quota, db_model=DBQuota
):

    async def user_quota(self, id: UUID) -> Optional[Sequence[Quota]]:
        return await self.get_models(true(), id=id)

    async def user_overQuota(self, id: UUID, resource: str) -> Optional[Quota]:
        return await self.get_model(
            text("user_id = :id AND resource = :resource"), id=id, resource=resource
        )


class UserDatasource(
    DatabaseRepository[DBUser, User], graph_model=User, db_model=DBUser
):

    async def query_people(self) -> Optional[Sequence[User]]:
        return await self.get_models(true())


class Context(BaseContext):
    quotas: QuotaDatasource
    users: UserDatasource

    def __init__(self, session_maker: async_sessionmaker):
        self.quotas = QuotaDatasource(session_maker)
        self.users = UserDatasource(session_maker)
