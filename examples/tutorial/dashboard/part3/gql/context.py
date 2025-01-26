from __future__ import annotations
from cannula.context import Context as BaseContext
from cannula.datasource.orm import DatabaseRepository
from sqlalchemy import true
from sqlalchemy.ext.asyncio import async_sessionmaker
from typing import Optional, Sequence
from .sql import DBUser
from .types import User


class UserDatasource(
    DatabaseRepository[DBUser, User], graph_model=User, db_model=DBUser
):

    async def query_people(self) -> Optional[Sequence[User]]:
        return await self.get_models(true())


class Context(BaseContext):
    users: UserDatasource

    def __init__(self, session_maker: async_sessionmaker):
        self.users = UserDatasource(session_maker)
