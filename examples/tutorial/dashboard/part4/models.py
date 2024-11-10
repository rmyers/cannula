from typing import List
from cannula.context import ResolveInfo
from cannula.contrib.orm import DBMixin
from sqlalchemy import select

from ..core.database import User as DBUser, Quota as DBQuota
from ._generated import UserTypeBase, QuotaType, QuotaTypeBase
from .context import Context


class Quota(QuotaTypeBase, DBMixin[DBQuota]):
    """Quota instance"""


class User(UserTypeBase, DBMixin[DBUser]):
    """User instance"""

    async def quota(self, info: ResolveInfo[Context]) -> List[QuotaType] | None:
        async with info.context.session() as session:
            query = select(DBQuota).where(DBQuota.user_id == self.id)
            quotas = await session.scalars(query)
            return [Quota.from_db(q) for q in quotas]

    async def overQuota(
        self, info: ResolveInfo[Context], *, resource: str
    ) -> QuotaType | None:
        async with info.context.session() as session:
            query = select(DBQuota).where(DBQuota.user_id == self.id)
            quotas: list[DBQuota] = await session.scalars(query)
            for q in quotas:
                if q.resource == resource:
                    return Quota.from_db(q)
