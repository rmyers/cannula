from __future__ import annotations
from abc import ABC, abstractmethod
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
    user_id: UUID
    user: Optional[User] = None
    resource: Optional[str] = None
    limit: Optional[int] = None
    count: Optional[int] = None


@dataclass(kw_only=True)
class User(ABC):
    """User Model"""

    __typename = "User"
    id: UUID
    name: Optional[str] = None
    email: Optional[str] = None
    quota: Optional[Sequence[Quota]] = None

    @abstractmethod
    async def overQuota(
        self, info: ResolveInfo["Context"], resource: str
    ) -> Optional[Quota]: ...


class peopleQuery(Protocol):

    async def __call__(
        self, info: ResolveInfo["Context"]
    ) -> Optional[Sequence[User]]: ...


class RootType(TypedDict, total=False):
    people: Optional[peopleQuery]
