from __future__ import annotations
from abc import ABC
from cannula import ResolveInfo
from dataclasses import dataclass
from typing import Optional, Protocol, Sequence, TYPE_CHECKING
from typing_extensions import TypedDict
from uuid import UUID

if TYPE_CHECKING:
    from .context import Context


@dataclass(kw_only=True)
class Quota(ABC):
    __typename = "Quota"
    id: UUID
    user_id: UUID
    resource: str
    limit: int
    count: int

    async def user(self, info: ResolveInfo["Context"]) -> Optional[User]:
        return await info.context.users.get_model_by_pk(self.user_id)


@dataclass(kw_only=True)
class User(ABC):
    __typename = "User"
    id: UUID
    name: str
    email: str

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


class personQuery(Protocol):

    async def __call__(
        self, info: ResolveInfo["Context"], id: UUID
    ) -> Optional[User]: ...


class RootType(TypedDict, total=False):
    people: Optional[peopleQuery]
    person: Optional[personQuery]
