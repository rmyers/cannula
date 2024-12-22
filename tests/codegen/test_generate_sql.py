from cannula import gql
from cannula.codegen import parse_schema
from cannula.codegen.generate_sql import generate_sqlalchemy_models
from cannula.format import format_code

SCHEMA = gql(
    '''
"""
User in the system

@metadata(
    db_table="users",
)
"""
type User {
    "User ID @metadata(primary_key: true)"
    id: ID!
    name: String!
    email: String!
    age: Int
    projects(limit: Int = 10): [Project]
    is_active: Boolean
}

"""
Project for users to work on

@metadata(db_table="projects")
"""
type Project {
    "Project ID @metadata(primary_key: true)"
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


def test_generate_sql():
    schema = parse_schema([SCHEMA, EXTENTIONS], [])
    source_code = generate_sqlalchemy_models(schema._schema)
    formatted_code = format_code(source_code)

    expected_code = """"""
    assert formatted_code == expected_code
