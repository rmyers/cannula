from __future__ import annotations
from abc import ABC
from cannula import ResolveInfo
from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Optional, Protocol
from typing_extensions import TypedDict
from uuid import UUID


@dataclass(kw_only=True)
class ScaledType(ABC):
    __typename = "Scaled"
    id: Optional[UUID] = None
    created: Optional[datetime] = None
    birthday: Optional[date] = None
    smoke: Optional[time] = None
    meta: Optional[dict] = None


class scaledQuery(Protocol):

    async def __call__(self, info: ResolveInfo) -> Optional[ScaledType]: ...


class RootType(TypedDict, total=False):
    scaled: Optional[scaledQuery]