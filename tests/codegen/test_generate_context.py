from cannula import gql
from cannula.codegen import render_code
from cannula.errors import SchemaValidationError
import pytest

# Similar schema but with focus on relations and where clauses
SCHEMA = gql(
    '''
"""
User model
---
metadata:
    db_table: users
"""
type User {
    "User ID @metadata(primary_key: true)"
    id: ID!
    name: String!
    email: String!
    """
    User's posts
    ---
    metadata:
        where: "author_id = :id"
        args: id
    """
    posts: [Post]
    """
    Latest post
    ---
    metadata:
        where: "author_id = :id ORDER BY created_at DESC LIMIT 1"
        args: id
    """
    latestPost: Post
}

"""
Post model
---
metadata:
    db_table: posts
"""
type Post {
    "Post ID @metadata(primary_key: true)"
    id: ID!
    title: String!
    "@metadata(foreign_key: users.id)"
    author_id: ID!
    author: User
}

type RemoteType {
    id: ID!
    name: String!
}
'''
)

EXPECTED = """\
from __future__ import annotations
from cannula.context import Context as BaseContext
from cannula.datasource.orm import DatabaseRepository
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker
from typing import Optional, Sequence
from .sql import DBPost, DBUser
from .types import Post, User


class PostDatasource(
    DatabaseRepository[DBPost, Post], graph_model=Post, db_model=DBPost
):

    async def user_posts(self, id: str) -> Optional[Sequence[Post]]:
        return await self.get_models(text("author_id = :id"), id=id)

    async def user_latestPost(self, id: str) -> Optional[Post]:
        return await self.get_model(
            text("author_id = :id ORDER BY created_at DESC LIMIT 1"), id=id
        )


class UserDatasource(
    DatabaseRepository[DBUser, User], graph_model=User, db_model=DBUser
):
    pass


class Context(BaseContext):
    posts: PostDatasource
    users: UserDatasource

    def __init__(self, session_maker: async_sessionmaker):
        self.posts = PostDatasource(session_maker)
        self.users = UserDatasource(session_maker)
"""


def test_generate_context():
    formatted_code = render_code([SCHEMA], [])
    assert formatted_code["context"] == EXPECTED


INVALID_RELATION = gql(
    '''
"""
User model
---
metadata:
    db_table: users
"""
type User {
    "User ID @metadata(primary_key: true)"
    id: ID!
    """
    Latest post without where clause
    """
    latestPost: Post
}

"""
Post model
---
metadata:
    db_table: posts
"""
type Post {
    id: ID!
    title: String!
}
'''
)

INVALID_LIST_FK = gql(
    '''
"""
User model
---
metadata:
    db_table: users
"""
type User {
    "User ID @metadata(primary_key: true)"
    id: ID!
    name: String!
}

"""
Post model
---
metadata:
    db_table: posts
"""
type Post {
    id: ID!
    "@metadata(foreign_key: users.id)"
    author_id: ID!
    "Invalid list relation with foreign key"
    authors: [User]
}
'''
)


@pytest.mark.parametrize(
    "schema,expected",
    [
        pytest.param(
            [INVALID_RELATION],
            "Field<User.latestPost> includes a relation to Post that requires a 'where' "
            "metadata attribute like 'user_id = :id' to preform the query.",
            id="missing-where-clause",
        ),
        pytest.param(
            [INVALID_LIST_FK],
            r"Field<Post.authors> is related via Field<Post.author_id> but \[User\] is a list. "
            r"Either change the reponse type to be singular or provide 'where' and 'args' to retrieve data.",
            id="invalid-list-fk",
        ),
    ],
)
def test_generate_context_errors(schema, expected):
    with pytest.raises(SchemaValidationError, match=expected):
        render_code(schema, [])
