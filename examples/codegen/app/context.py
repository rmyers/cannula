from __future__ import annotations
from cannula.context import Context as BaseContext
from cannula.datasource.orm import DatabaseRepository
from sqlalchemy.ext.asyncio import async_sessionmaker
from .sql import DBQuota, DBUser
from .types import Quota, User


class QuotaDatasource(
    DatabaseRepository[DBQuota, Quota], graph_model=Quota, db_model=DBQuota
):
    pass


class UserDatasource(
    DatabaseRepository[DBUser, User], graph_model=User, db_model=DBUser
):
    pass


class Context(BaseContext):
    quotas: QuotaDatasource
    users: UserDatasource

    def __init__(self, session_maker: async_sessionmaker):
        self.quotas = QuotaDatasource(session_maker)
        self.users = UserDatasource(session_maker)
