from cannula import gql
from cannula.codegen import render_code
import pytest

SCHEMA = gql(
    '''
"""
User type with computed and non-computed fields
"""
type User {
    id: ID!
    name: String!
    email: String!
    "Computed field with required args"
    posts(limit: Int!): [Post]
    "Computed field with optional args"
    latestPost(includeUnpublished: Boolean = false): Post
}

"""
Post type with relationship back to User
"""
type Post {
    id: ID!
    title: String!
    authorId: ID!
    "Computed field with no args"
    author: User
}

"""
Input type for creating users
"""
input CreateUserInput {
    name: String!
    email: String!
}

"""
Interface for entities with timestamps
"""
interface Timestamped {
    createdAt: String!
    updatedAt: String!
}

"""
Union of possible feed items
"""
union FeedItem = Post | User
'''
)

EXTENSIONS = gql(
    '''
extend type Query {
    """
    Get user by id
    """
    user(id: ID!): User
    "Get feed items"
    feed(limit: Int = 10): [FeedItem]
}
'''
)

EXPECTED = '''\
from __future__ import annotations
from abc import ABC
from cannula import ResolveInfo
from dataclasses import dataclass
from typing import Optional, Protocol, Sequence, TYPE_CHECKING, Union
from typing_extensions import TypedDict

if TYPE_CHECKING:
    from .context import Context


class Timestamped(Protocol):
    """Interface for entities with timestamps"""

    createdAt: str
    updatedAt: str


class CreateUserInput(TypedDict):
    """Input type for creating users"""

    name: str
    email: str


@dataclass(kw_only=True)
class Post(ABC):
    """Post type with relationship back to User"""

    __typename = "Post"
    id: str
    title: str
    authorId: str

    async def author(self, info: ResolveInfo["Context"]) -> Optional[User]:
        """Computed field with no args"""
        return await info.context.users.post_author()


@dataclass(kw_only=True)
class User(ABC):
    """User type with computed and non-computed fields"""

    __typename = "User"
    id: str
    name: str
    email: str

    async def posts(
        self, info: ResolveInfo["Context"], limit: int
    ) -> Optional[Sequence[Post]]:
        """Computed field with required args"""
        return await info.context.posts.user_posts(limit=limit)

    async def latestPost(
        self, info: ResolveInfo["Context"], *, includeUnpublished: bool = False
    ) -> Optional[Post]:
        """Computed field with optional args"""
        return await info.context.posts.user_latestPost(
            includeUnpublished=includeUnpublished
        )


FeedItem = Union[Post, User]


class feedQuery(Protocol):

    async def __call__(
        self, info: ResolveInfo["Context"], *, limit: int = 10
    ) -> Optional[Sequence[FeedItem]]:
        """Get feed items"""
        ...


class userQuery(Protocol):

    async def __call__(self, info: ResolveInfo["Context"], id: str) -> Optional[User]:
        """Get user by id"""
        ...


class RootType(TypedDict, total=False):
    feed: Optional[feedQuery]
    user: Optional[userQuery]
'''


def test_generate_types():
    formatted_code = render_code([SCHEMA, EXTENSIONS], [])
    assert formatted_code["types"] == EXPECTED


def test_generate_types_pydantic():
    formatted_code = render_code([SCHEMA, EXTENSIONS], [], use_pydantic=True)
    # Just verify key differences from regular generation
    assert "from pydantic import BaseModel" in formatted_code["types"]
    assert "@dataclass" not in formatted_code["types"]
    assert "class User(BaseModel):" in formatted_code["types"]
    assert "class Post(BaseModel):" in formatted_code["types"]


INVALID_RELATION = gql(
    """
type User {
    id: ID!
    "Invalid computed field without proper type"
    posts: [InvalidType]
}
"""
)

INVALID_ARGS = gql(
    """
type User {
    id: ID!
    "Invalid required argument type"
    posts(limit: InvalidType!): [Post]
}

type Post {
    id: ID!
}
"""
)


@pytest.mark.parametrize(
    "schema,expected",
    [
        pytest.param(
            [INVALID_RELATION],
            "Unknown type 'InvalidType'",
            id="invalid-type-reference",
        ),
        pytest.param(
            [INVALID_ARGS],
            "Unknown type 'InvalidType'",
            id="invalid-argument-type",
        ),
    ],
)
def test_generate_types_errors(schema, expected):
    with pytest.raises(Exception, match=expected):
        render_code(schema, [])
