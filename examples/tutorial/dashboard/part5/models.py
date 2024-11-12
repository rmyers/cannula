import logging

import uuid

from typing import (
    Any,
    Awaitable,
    ClassVar,
    Dict,
    Generic,
    List,
    Protocol,
    Sequence,
    TypeVar,
    TYPE_CHECKING,
    cast,
)

from cannula.context import ResolveInfo

from ..core.database import User as DBUser, Quota as DBQuota
from ._generated import UserType, QuotaType

from cannula.datasource.orm import DatabaseRepository

LOG = logging.getLogger(__name__)

if TYPE_CHECKING:  # pragma: no cover
    from .context import Context


class User(UserType):
    """User instance"""

    async def quota(self, info: ResolveInfo["Context"]) -> List["Quota"] | None:
        return await info.context.quota_repo.get_quota_for_user(self.id)

    async def overQuota(
        self, info: ResolveInfo["Context"], *, resource: str
    ) -> "Quota | None":
        return await info.context.quota_repo.get_over_quota(self.id, resource=resource)


class Quota(QuotaType):
    pass


class UserRepository(
    DatabaseRepository[DBUser, User],
    db_model=DBUser,
    graph_model=User,
):
    pass


class QuotaRepository(
    DatabaseRepository[DBQuota, Quota],
    db_model=DBQuota,
    graph_model=Quota,
):

    async def get_quota_for_user(self, id: uuid.UUID) -> List[Quota]:
        return await self.get_models(DBQuota.user_id == id)

    async def get_over_quota(self, id: uuid.UUID, resource: str) -> Quota | None:
        return await self.get_model_by_query(
            DBQuota.user_id == id, DBQuota.resource == resource
        )
