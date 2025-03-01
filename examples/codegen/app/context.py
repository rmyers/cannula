from __future__ import annotations
from cannula.context import Context as BaseContext
from cannula.datasource.http import HTTPDatasource
from cannula.datasource.orm import DatabaseRepository
from cannula.types import ConnectHTTP, HTTPHeaderMapping, SourceHTTP
from sqlalchemy import text, true
from sqlalchemy.ext.asyncio import async_sessionmaker
from typing import Optional, Protocol, Sequence
from uuid import UUID
from .sql import DBQuota, DBUser
from .types import Product, Quota, User


class QuotaDatasource(
    DatabaseRepository[DBQuota, Quota], graph_model=Quota, db_model=DBQuota
):

    async def user_quota(self, id: UUID) -> Optional[Sequence[Quota]]:
        return await self.get_models(true())

    async def user_overQuota(self, id: UUID, resource: str) -> Optional[Quota]:
        return await self.get_model(
            text("user_id = :id AND resource = :resource").bindparams(
                id=id, resource=resource
            )
        )


class UserDatasource(
    DatabaseRepository[DBUser, User], graph_model=User, db_model=DBUser
):

    async def query_people(self) -> Optional[Sequence[User]]:
        return await self.get_models(true())


class Frank_ApiHTTPDatasource(
    HTTPDatasource,
    source=SourceHTTP(
        baseURL="$config.brains",
        headers=[
            HTTPHeaderMapping(name="Bad", from_header="Boo", value="$config.meat")
        ],
    ),
):

    async def quota_products(self, **variables) -> Optional[Sequence[Product]]:
        response = await self.execute_operation(
            connect_http=ConnectHTTP(
                GET="/products",
                POST=None,
                PUT=None,
                PATCH=None,
                DELETE=None,
                headers=[
                    HTTPHeaderMapping(
                        name="Authorization", from_header=None, value="$config.black"
                    )
                ],
                body=None,
            ),
            selection="$.products[] { id name price }",
            variables=variables,
        )
        return await self.get_models(model=Product, response=response)


class Settings(Protocol):
    black: str
    brains: str
    meat: str

    @property
    def session(self) -> async_sessionmaker: ...

    @property
    def readonly_session(self) -> Optional[async_sessionmaker]: ...


class Context(BaseContext[Settings]):
    quotas: QuotaDatasource
    users: UserDatasource
    frank_api: Frank_ApiHTTPDatasource

    def init(self):
        self.quotas = QuotaDatasource(self.config.session)
        self.users = UserDatasource(self.config.session)
        self.frank_api = Frank_ApiHTTPDatasource(
            config=self.config, request=self.request
        )
