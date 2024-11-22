from typing import TYPE_CHECKING
import uuid

import cannula
from cannula.datasource.orm import DatabaseRepository

from ..core.database import User as DBUser, Quota as DBQuota
from ._generated import UserType, QuotaType

# This is to avoid circular imports, we only need this reference for
# checking types in like: `cannula.ResolveInfo["Context"]`
if TYPE_CHECKING:
    from .context import Context


class User(UserType):
    """User Graph Model"""

    async def quota(self, info: cannula.ResolveInfo["Context"]) -> list["Quota"] | None:
        return await info.context.quota_repo.get_quota_for_user(self.id)

    async def overQuota(
        self, info: cannula.ResolveInfo["Context"], *, resource: str
    ) -> "Quota | None":
        return await info.context.quota_repo.get_over_quota(self.id, resource=resource)


class Quota(QuotaType):
    """Quota Graph Model"""


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

    async def get_quota_for_user(self, id: uuid.UUID) -> list[Quota]:
        return await self.get_models(DBQuota.user_id == id)

    async def get_over_quota(self, id: uuid.UUID, resource: str) -> Quota | None:
        return await self.get_model_by_query(
            DBQuota.user_id == id, DBQuota.resource == resource
        )
