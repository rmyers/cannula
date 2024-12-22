from cannula import gql
from cannula.codegen import parse_schema
from cannula.codegen.generate_sql import (
    SchemaValidationError,
    generate_sqlalchemy_models,
)
from cannula.format import format_code
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
from sqlalchemy import Integer, String, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    """User in the system

    Args:
        id: User ID"""

    __tablename__ = "users"
    id: Mapped = mapped_column(String, primary_key=True)
    name: Mapped = mapped_column(String, index=True, nullable=False)
    email: Mapped = mapped_column(
        String, unique=True, name="email_address", nullable=False
    )
    age: Mapped = mapped_column(Integer, nullable=True)
    projects: Mapped = mapped_column(String, nullable=True)
    is_active: Mapped = mapped_column(Boolean, nullable=True)


class Project(Base):
    """Project for users to work on

    Args:
        id: Project ID"""

    __tablename__ = "projects"
    id: Mapped = mapped_column(String, primary_key=True)
    name: Mapped = mapped_column(String, nullable=False)
    description: Mapped = mapped_column(String, nullable=True)
    is_active: Mapped = mapped_column(Boolean, nullable=True)
'''


def test_generate_sql():
    schema = parse_schema([SCHEMA, EXTENTIONS], [])
    source_code = generate_sqlalchemy_models(schema._schema)
    formatted_code = format_code(source_code)

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
        _schema = parse_schema(schema, [])
        generate_sqlalchemy_models(_schema._schema)
