from cannula import gql
from cannula.codegen.generate_sql import (
    SchemaValidationError,
    render_sql_models,
)
import pytest

SCHEMA = gql(
    '''
"""
User in the system

---
metadata:
    db_table: users
    cache: false
    ttl: 0
    weight: 1.2
"""
type User {
    "User ID @metadata(primary_key: true)"
    id: ID!
    "@metadata(index: true)"
    name: String!
    "@metadata(db_column: email_address, unique: true)"
    email: String!
    "@metadata(nullable: true, cache: false)"
    age: Int
    projects(limit: Int = 10): [Project]
    is_active: Boolean
}

"""
Project for users to work on

@metadata(db_table:"projects")
"""
type Project {
    "Project ID @metadata(primary_key: true)"
    id: ID!
    name: String!
    description: String
    "@metadata(wieght: 1.5, fancy: $100)"
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
    """
extend type Query {
    user(id: ID!): User
    projects(userId: ID!): [Project]
}
"""
)

EXPECTED = '''\
from __future__ import annotations
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from typing import Optional, Sequence


class Base(DeclarativeBase):
    pass


class Project(Base):
    """Project for users to work on"""

    __tablename__ = "projects"
    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[Optional[str]] = mapped_column(nullable=True)
    is_active: Mapped[Optional[bool]] = mapped_column(nullable=True)


class User(Base):
    """User in the system"""

    __tablename__ = "users"
    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(index=True, nullable=False)
    email: Mapped[str] = mapped_column(
        unique=True, name="email_address", nullable=False
    )
    age: Mapped[Optional[int]] = mapped_column(nullable=True)
    projects: Mapped[Optional[Sequence[ProjectType]]] = mapped_column(nullable=True)
    is_active: Mapped[Optional[bool]] = mapped_column(nullable=True)
'''


def test_generate_sql():
    formatted_code = render_sql_models([SCHEMA, EXTENTIONS], [])

    assert formatted_code == EXPECTED


INVALID_NULLABLE = gql(
    """
"@metadata(db_table:users)"
type User {
    "User ID @metadata(primary_key: true)"
    id: ID!
    "@metadata(nullable: true, index: true)"
    name: String!
}
"""
)

INVALID_COMPOSITE = gql(
    """
"@metadata(db_table:users)"
type User {
    "User ID @metadata(primary_key: true)"
    id: ID!
    "@metadata(primary_key: true)"
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
    ],
)
def test_generate_sql_errors(schema, expected):
    with pytest.raises(SchemaValidationError, match=expected):
        render_sql_models(schema, [])
