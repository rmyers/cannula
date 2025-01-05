from cannula import gql
from cannula.codegen import render_code
from cannula.codegen.generate_sql import SchemaValidationError
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
    "@metadata(foreign_key: users.id)"
    author_id: ID!
    """
    Author of the project

    ---
    metadata:
        relation:
            back_populates: "projects"
            cascade: "all, delete-orphan"
    """
    author: User!
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
from sqlalchemy import ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
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
    author: Mapped[DBUser] = relationship(
        "DBUser", back_populates="projects", cascade="all, delete-orphan"
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

INVALID_RELATION = gql(
    '''
"@metadata(db_table:users)"
type User {
    "User ID @metadata(primary_key: true)"
    id: ID!
    "@metadata(foreign_key: projects.id)"
    project_id: String!
    """
    User's project

    ---
    metadata:
        relation:
            back_populates: "author"
            cascade: "all, delete-orphan"
    """
    project: Project
}

"not a db table"
type Project {
    id: ID!
    name: String!
}
'''
)

INVALID_RELATION_TYPE = gql(
    '''
"@metadata(db_table:users)"
type User {
    "User ID @metadata(primary_key: true)"
    id: ID!
    "@metadata(foreign_key: projects.id)"
    project_id: String!
    """
    User's project @metadata(relation: "projects")
    """
    project: String
}
'''
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
            "Relationship User.project references type DBProject which is not marked as a database table",
            id="invalid-relation",
        ),
        pytest.param(
            [INVALID_RELATION_TYPE],
            "Relation metadata for User.project must be a dictionary",
            id="invalid-relation-type",
        ),
    ],
)
def test_generate_sql_errors(schema, expected):
    with pytest.raises(SchemaValidationError, match=expected):
        render_code(schema, [])
