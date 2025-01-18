from __future__ import annotations
from cannula import ResolveInfo
from pydantic import BaseModel
from typing import Optional, Protocol, Sequence, TYPE_CHECKING
from typing_extensions import TypedDict
from uuid import UUID

if TYPE_CHECKING:
    from .context import Context


class Quota(BaseModel):
    __typename = "Quota"
    user_id: UUID
    resource: Optional[str] = None
    limit: Optional[int] = None
    count: Optional[int] = None

    async def user(self, info: ResolveInfo["Context"]) -> Optional[User]:
        """User that this quota is for."""
        return await info.context.users.quota_user()


class User(BaseModel):
    """User Model"""

    __typename = "User"
    id: UUID
    name: Optional[str] = None
    email: Optional[str] = None

    async def quota(self, info: ResolveInfo["Context"]) -> Optional[Sequence[Quota]]:
        return await info.context.quotas.user_quota(id=self.id)

    async def overQuota(
        self, info: ResolveInfo["Context"], resource: str
    ) -> Optional[Quota]:
        return await info.context.quotas.user_overQuota(id=self.id, resource=resource)


class peopleQuery(Protocol):

    async def __call__(
        self, info: ResolveInfo["Context"]
    ) -> Optional[Sequence[User]]: ...


class RootType(TypedDict, total=False):
    people: Optional[peopleQuery]
