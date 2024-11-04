from typing import List, cast
from cannula.context import ResolveInfo
from cannula.contrib.orm import DBMixin

from ..core.database import User as DBUser, Quota as DBQuota
from ._generated import UserTypeBase, QuotaType, QuotaTypeBase
from .context import Context


class Quota(QuotaTypeBase, DBMixin[DBQuota]):
    """Quota instance"""


class User(UserTypeBase, DBMixin[DBUser]):
    """User instance"""

    async def quota(self, info: ResolveInfo[Context]) -> List[QuotaType] | None:
        quotas: list[DBQuota] = await self._db_model.awaitable_attrs.quota
        return [Quota.from_db(q) for q in quotas]

    async def overQuota(
        self, info: ResolveInfo[Context], *, resource: str
    ) -> QuotaType | None:
        quotas: list[DBQuota] = await self._db_model.awaitable_attrs.quota
        for q in quotas:
            if q.resource == resource:
                return Quota.from_db(q)
