from typing import List
from cannula.context import ResolveInfo
from sqlalchemy import select

from ..core.database import User as DBUser, Quota as DBQuota
from ._generated import UserType, QuotaType
from .context import Context


class Quota(QuotaType):
    """Quota instance"""

    @classmethod
    def from_db(cls, db_quota: DBQuota) -> "Quota":
        """Constructor for creating quota from db object"""
        return cls(
            resource=db_quota.resource,
            limit=db_quota.limit,
            count=db_quota.count,
        )


class User(UserType):
    """User instance"""

    @classmethod
    def from_db(cls, db_user: DBUser) -> "User":
        """Constructor for creating user from db object"""
        return cls(
            id=db_user.id,
            name=db_user.name,
            email=db_user.email,
        )

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
