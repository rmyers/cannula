from __future__ import annotations
from abc import ABC
from cannula import ResolveInfo
from dataclasses import dataclass
from typing import Optional, Protocol, Sequence
from typing_extensions import TypedDict
from uuid import UUID


class PersonaType(Protocol):
    id: UUID
    name: Optional[str] = None
    email: Optional[str] = None


class ResourceType(Protocol):
    quota: Optional[QuotaType] = None
    user: Optional[UserType] = None
    created: Optional[str] = None


@dataclass(kw_only=True)
class AdminType(ABC):
    __typename = "Admin"
    id: UUID
    name: Optional[str] = None
    email: Optional[str] = None


@dataclass(kw_only=True)
class BoardType(ABC):
    __typename = "Board"
    id: Optional[str] = None
    quota: Optional[QuotaType] = None
    user: Optional[UserType] = None
    title: Optional[str] = None
    created: Optional[str] = None
    posts: Optional[Sequence[PostType]] = None


@dataclass(kw_only=True)
class PostType(ABC):
    __typename = "Post"
    id: Optional[str] = None
    quota: Optional[QuotaType] = None
    user: Optional[UserType] = None
    title: Optional[str] = None
    created: Optional[str] = None
    body: Optional[str] = None


@dataclass(kw_only=True)
class QuotaType(ABC):
    __typename = "Quota"
    user: Optional[UserType] = None
    resource: Optional[str] = None
    limit: Optional[int] = None
    count: Optional[int] = None


@dataclass(kw_only=True)
class UserType(ABC):
    __typename = "User"
    id: UUID
    name: Optional[str] = None
    email: Optional[str] = None
    quota: Optional[Sequence[QuotaType]] = None


class addPostMutation(Protocol):
    async def __call__(
        self, info: ResolveInfo, board_id: str, post_id: str
    ) -> Optional[BoardType]:
        ...


class boardsQuery(Protocol):
    async def __call__(
        self,
        info: ResolveInfo,
        *,
        limit: Optional[int] = 100,
        offset: Optional[int] = 0,
    ) -> Optional[Sequence[BoardType]]:
        ...


class createBoardMutation(Protocol):
    async def __call__(self, info: ResolveInfo, title: str) -> Optional[BoardType]:
        ...


class createPostMutation(Protocol):
    async def __call__(
        self, info: ResolveInfo, title: str, body: str
    ) -> Optional[PostType]:
        ...


class deleteBoardMutation(Protocol):
    async def __call__(self, info: ResolveInfo, id: str) -> Optional[bool]:
        ...


class deletePostMutation(Protocol):
    async def __call__(self, info: ResolveInfo, id: str) -> Optional[bool]:
        ...


class editBoardMutation(Protocol):
    async def __call__(
        self, info: ResolveInfo, id: str, *, title: Optional[str] = None
    ) -> Optional[BoardType]:
        ...


class editPostMutation(Protocol):
    async def __call__(
        self,
        info: ResolveInfo,
        id: str,
        *,
        title: Optional[str] = None,
        body: Optional[str] = None,
    ) -> Optional[PostType]:
        ...


class meQuery(Protocol):
    async def __call__(self, info: ResolveInfo) -> Optional[PersonaType]:
        ...


class peopleQuery(Protocol):
    async def __call__(self, info: ResolveInfo) -> Optional[Sequence[PersonaType]]:
        ...


class postsQuery(Protocol):
    async def __call__(
        self,
        info: ResolveInfo,
        *,
        limit: Optional[int] = 100,
        offset: Optional[int] = 0,
    ) -> Optional[Sequence[PostType]]:
        ...


class userQuery(Protocol):
    async def __call__(
        self, info: ResolveInfo, *, id: Optional[str] = None
    ) -> Optional[UserType]:
        ...


class RootType(TypedDict, total=False):
    addPost: Optional[addPostMutation]
    boards: Optional[boardsQuery]
    createBoard: Optional[createBoardMutation]
    createPost: Optional[createPostMutation]
    deleteBoard: Optional[deleteBoardMutation]
    deletePost: Optional[deletePostMutation]
    editBoard: Optional[editBoardMutation]
    editPost: Optional[editPostMutation]
    me: Optional[meQuery]
    people: Optional[peopleQuery]
    posts: Optional[postsQuery]
    user: Optional[userQuery]
