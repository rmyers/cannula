from __future__ import annotations
from abc import ABC
from cannula import ResolveInfo
from dataclasses import dataclass
from typing import Optional, Protocol, Sequence, TYPE_CHECKING
from typing_extensions import TypedDict
from uuid import UUID

if TYPE_CHECKING:
    from .context import Context


class userCreate(TypedDict):
    name: str
    email: str


class userModify(TypedDict):
    id: str
    name: str
    email: str


@dataclass(kw_only=True)
class Product(ABC):
    __typename = "Product"
    id: str
    name: Optional[str] = None
    price: Optional[int] = None


@dataclass(kw_only=True)
class Quota(ABC):
    __typename = "Quota"
    user_id: UUID
    resource: Optional[str] = None
    limit: Optional[int] = None
    count: Optional[int] = None

    async def user(self, info: ResolveInfo["Context"]) -> Optional[User]:
        return await info.context.users.get_model_by_pk(self.user_id)

    async def products(
        self, info: ResolveInfo["Context"], id: str
    ) -> Optional[Sequence[Product]]:
        return await info.context.frank_api.quota_products(user_id=self.user_id, id=id)


@dataclass(kw_only=True)
class User(ABC):
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


class createPersonMutation(Protocol):

    async def __call__(
        self, info: ResolveInfo["Context"], user: userCreate
    ) -> Optional[User]: ...


class peopleQuery(Protocol):

    async def __call__(
        self, info: ResolveInfo["Context"]
    ) -> Optional[Sequence[User]]: ...


class updatePersonMutation(Protocol):

    async def __call__(
        self, info: ResolveInfo["Context"], user: userModify
    ) -> Optional[User]: ...


class RootType(TypedDict, total=False):
    createPerson: Optional[createPersonMutation]
    people: Optional[peopleQuery]
    updatePerson: Optional[updatePersonMutation]
