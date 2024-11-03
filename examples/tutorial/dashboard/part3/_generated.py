from __future__ import annotations
from abc import ABC
from cannula import ResolveInfo
from dataclasses import dataclass
from typing import List, Optional, Protocol, Union
from typing_extensions import TypedDict
from uuid import UUID


class PersonaType(Protocol):
    __typename = "Persona"
    id: UUID
    name: Optional[str] = None
    email: Optional[str] = None


class ResourceType(Protocol):
    __typename = "Resource"
    quota: Optional[QuotaType] = None
    user: Optional[UserType] = None
    created: Optional[str] = None


@dataclass(kw_only=True)
class AdminTypeBase(ABC):
    __typename = "Admin"
    id: UUID
    name: Optional[str] = None
    email: Optional[str] = None


class AdminTypeDict(TypedDict, total=False):
    id: UUID
    name: Optional[str]
    email: Optional[str]


AdminType = Union[AdminTypeBase, AdminTypeDict]


@dataclass(kw_only=True)
class BoardTypeBase(ABC):
    __typename = "Board"
    id: Optional[str] = None
    quota: Optional[QuotaType] = None
    user: Optional[UserType] = None
    title: Optional[str] = None
    created: Optional[str] = None
    posts: Optional[List[PostType]] = None


class BoardTypeDict(TypedDict, total=False):
    id: Optional[str]
    quota: Optional[QuotaType]
    user: Optional[UserType]
    title: Optional[str]
    created: Optional[str]
    posts: Optional[List[PostType]]


BoardType = Union[BoardTypeBase, BoardTypeDict]


@dataclass(kw_only=True)
class PostTypeBase(ABC):
    __typename = "Post"
    id: Optional[str] = None
    quota: Optional[QuotaType] = None
    user: Optional[UserType] = None
    title: Optional[str] = None
    created: Optional[str] = None
    body: Optional[str] = None


class PostTypeDict(TypedDict, total=False):
    id: Optional[str]
    quota: Optional[QuotaType]
    user: Optional[UserType]
    title: Optional[str]
    created: Optional[str]
    body: Optional[str]


PostType = Union[PostTypeBase, PostTypeDict]


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
    quota: Optional[List[QuotaType]] = None


class UserTypeDict(TypedDict, total=False):
    id: UUID
    name: Optional[str]
    email: Optional[str]
    quota: Optional[List[QuotaType]]


UserType = Union[UserTypeBase, UserTypeDict]


class addPostMutation(Protocol):
    async def __call__(
        self, info: ResolveInfo, board_id: str, post_id: str
    ) -> BoardType:
        ...


class boardsQuery(Protocol):
    async def __call__(
        self,
        info: ResolveInfo,
        *,
        limit: Optional[int] = 100,
        offset: Optional[int] = 0,
    ) -> List[BoardType]:
        ...


class createBoardMutation(Protocol):
    async def __call__(self, info: ResolveInfo, title: str) -> BoardType:
        ...


class createPostMutation(Protocol):
    async def __call__(self, info: ResolveInfo, title: str, body: str) -> PostType:
        ...


class deleteBoardMutation(Protocol):
    async def __call__(self, info: ResolveInfo, id: str) -> bool:
        ...


class deletePostMutation(Protocol):
    async def __call__(self, info: ResolveInfo, id: str) -> bool:
        ...


class editBoardMutation(Protocol):
    async def __call__(
        self, info: ResolveInfo, id: str, *, title: Optional[str] = None
    ) -> BoardType:
        ...


class editPostMutation(Protocol):
    async def __call__(
        self,
        info: ResolveInfo,
        id: str,
        *,
        title: Optional[str] = None,
        body: Optional[str] = None,
    ) -> PostType:
        ...


class meQuery(Protocol):
    async def __call__(self, info: ResolveInfo) -> PersonaType:
        ...


class peopleQuery(Protocol):
    async def __call__(self, info: ResolveInfo) -> List[PersonaType]:
        ...


class postsQuery(Protocol):
    async def __call__(
        self,
        info: ResolveInfo,
        *,
        limit: Optional[int] = 100,
        offset: Optional[int] = 0,
    ) -> List[PostType]:
        ...


class userQuery(Protocol):
    async def __call__(
        self, info: ResolveInfo, *, id: Optional[str] = None
    ) -> UserType:
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
