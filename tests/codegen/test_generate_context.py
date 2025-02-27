from cannula import gql
from cannula.codegen import render_code
from cannula.errors import SchemaValidationError
import pytest

# Similar schema but with focus on relations and where clauses
SCHEMA = gql(
    '''
"""
User model
Here
"""
type User @db_sql {
    id: ID! @field_meta(primary_key: true)
    name: String!
    email: String!
    posts: [Post] @field_meta(where: "author_id = :id", args: ["id"])
    latestPost: Post @field_meta(where: "author_id = :id ORDER BY created_at DESC LIMIT 1", args: ["id"])
}

"""
Post model
"""
type Post @db_sql {
    id: ID! @field_meta(primary_key: true)
    title: String!
    author_id: ID! @field_meta(foreign_key: "users.id")
    author: User
}

"""
Remote Type is not a db model
"""
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
from typing import Optional, Protocol, Sequence
from .sql import DBPost, DBUser
from .types import Post, User


class PostDatasource(
    DatabaseRepository[DBPost, Post], graph_model=Post, db_model=DBPost
):

    async def user_posts(self, id: str) -> Optional[Sequence[Post]]:
        return await self.get_models(text("author_id = :id").bindparams(id=id))

    async def user_latestPost(self, id: str) -> Optional[Post]:
        return await self.get_model(
            text("author_id = :id ORDER BY created_at DESC LIMIT 1").bindparams(id=id)
        )


class UserDatasource(
    DatabaseRepository[DBUser, User], graph_model=User, db_model=DBUser
):
    pass


class Settings(Protocol):

    @property
    def session(self) -> async_sessionmaker: ...

    @property
    def readonly_session(self) -> Optional[async_sessionmaker]: ...


class Context(BaseContext[Settings]):
    posts: PostDatasource
    users: UserDatasource

    def init(self):
        self.posts = PostDatasource(self.config.session)
        self.users = UserDatasource(self.config.session)
"""


def test_generate_context():
    formatted_code = render_code([SCHEMA], [])
    assert formatted_code["context"] == EXPECTED


INVALID_RELATION = gql(
    """
type User @db_sql {
    id: ID!  @field_meta(primary_key: true)
    "Invalid relation missing where clause"
    latestPost: Post
}
type Post @db_sql {
    id: ID!
    title: String!
}
"""
)

INVALID_LIST_FK = gql(
    """
type User @db_sql {
    id: ID! @field_meta(primary_key: true)
    name: String!
}

type Post {
    id: ID! @field_meta(primary_key: true)
    author_id: ID!  @field_meta(foreign_key: "users.id")
    "Invalid list relation with foreign key"
    authors: [User]
}
"""
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
