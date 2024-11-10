from __future__ import annotations
from abc import ABC, abstractmethod
from cannula import ResolveInfo
from dataclasses import dataclass
from typing import List, Optional, Protocol, Sequence, Union
from typing_extensions import TypedDict
from uuid import UUID


@dataclass(kw_only=True)
class QuotaTypeBase(ABC):
    __typename = "Quota"
    user: Optional[UserType] = None
    resource: Optional[str] = None
    limit: Optional[int] = None
    count: Optional[int] = None


class QuotaTypeDict(TypedDict, total=False):
    user: Optional[UserType]
    resource: Optional[str]
    limit: Optional[int]
    count: Optional[int]


QuotaType = Union[QuotaTypeBase, QuotaTypeDict]


@dataclass(kw_only=True)
class UserTypeBase(ABC):
    __typename = "User"
    id: UUID
    name: Optional[str] = None
    email: Optional[str] = None

    @abstractmethod
    async def quota(self, info: ResolveInfo) -> Optional[List[QuotaType]]: ...

    @abstractmethod
    async def overQuota(
        self, info: ResolveInfo, resource: str
    ) -> Optional[QuotaType]: ...


class UserTypeDict(TypedDict, total=False):
    id: UUID
    name: Optional[str]
    email: Optional[str]
    quota: Optional[List[QuotaType]]
    overQuota: Optional[QuotaType]


UserType = Union[UserTypeBase, UserTypeDict]


class peopleQuery(Protocol):
    async def __call__(self, info: ResolveInfo) -> Sequence[UserType]: ...


class personQuery(Protocol):
    async def __call__(self, info: ResolveInfo, id: UUID) -> Optional[UserType]: ...


class RootType(TypedDict, total=False):
    people: Optional[peopleQuery]
    person: Optional[personQuery]
