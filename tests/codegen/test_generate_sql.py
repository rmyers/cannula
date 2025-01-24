from cannula import gql
from cannula.codegen import render_code
from cannula.codegen.generate_sql import SchemaValidationError
import pytest

SCHEMA = gql(
    '''
"""
User in the system
"""
type User @db_sql {
    "User ID"
    id: ID! @field_meta(primary_key: true)
    name: String! @field_meta(index: true)
    email: String! @field_meta(db_column: "email_address", unique: true)
    age: Int @field_meta(nullable: true)
    """
    User Projects
    """
    projects(limit: Int = 10): [Project] @field_meta(where: "author_id = :id")
    is_active: Boolean
}

"""
Project for users to work on
"""
type Project @db_sql {
    "Project ID"
    id: ID!  @field_meta(primary_key: true)
    name: String!
    author_id: ID!  @field_meta(foreign_key: "users.id")
    author: User!
    description: String
    is_active: Boolean
}

"""
Remote Resource that is not connected to a database table
"""
type RemoteResourceWithoutDB {
    id: ID!
    name: String!
    description: String
    is_active: Boolean
}
'''
)

EXTENTIONS = gql(
    '''
extend type Query {
    """
    User by id
    """
    user(id: ID!): User @field_meta(where: "id = :id")
    projects(userId: ID!): [Project]
}
'''
)

EXPECTED = '''\
from __future__ import annotations
from sqlalchemy import ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from typing import Optional


class Base(DeclarativeBase):
    pass


class DBProject(Base):
    """Project for users to work on"""

    __tablename__ = "projects"
    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
    author_id: Mapped[str] = mapped_column(
        foreign_key=ForeignKey("users.id"), nullable=False
    )
    description: Mapped[Optional[str]] = mapped_column(nullable=True)
    is_active: Mapped[Optional[bool]] = mapped_column(nullable=True)


class DBUser(Base):
    """User in the system"""

    __tablename__ = "users"
    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(index=True, nullable=False)
    email: Mapped[str] = mapped_column(
        unique=True, name="email_address", nullable=False
    )
    age: Mapped[Optional[int]] = mapped_column(nullable=True)
    is_active: Mapped[Optional[bool]] = mapped_column(nullable=True)
'''


def test_generate_sql():
    formatted_code = render_code([SCHEMA, EXTENTIONS], [])

    assert formatted_code["sql"] == EXPECTED


INVALID_NULLABLE = gql(
    """
type User @db_sql {
    id: ID! @field_meta(primary_key: true)
    name: String! @field_meta(nullable: true, index: true)
}
"""
)

INVALID_COMPOSITE = gql(
    """
type User @db_sql {
    id: ID! @field_meta(primary_key: true)
    name: String! @field_meta(primary_key: true)
}
"""
)

INVALID_RELATION = gql(
    """
type User @db_sql {
    id: ID! @field_meta(primary_key: true)
    project_id: String! @field_meta(foreign_key: "projects.id")
}

"not a db table"
type Project {
    id: ID!
    name: String!
}
"""
)


@pytest.mark.parametrize(
    "schema, expected",
    [
        pytest.param(
            [INVALID_NULLABLE],
            "Field 'name' is marked as non-null in GraphQL schema",
            id="invlid-nullable",
        ),
        pytest.param(
            [INVALID_COMPOSITE],
            "Multiple primary keys found in type 'User': id, name.",
            id="invalid-composite",
        ),
        pytest.param(
            [INVALID_RELATION],
            "Field<User.project_id> references foreign_key 'projects.id' which is not marked as a database table",
            id="invalid-relation",
        ),
    ],
)
def test_generate_sql_errors(schema, expected):
    with pytest.raises(SchemaValidationError, match=expected):
        render_code(schema, [])
