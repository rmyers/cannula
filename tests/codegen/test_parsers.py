import pytest
from graphql import (
    GraphQLField,
    GraphQLArgument,
    GraphQLInputObjectType,
    GraphQLString,
    GraphQLInt,
    GraphQLFloat,
    GraphQLBoolean,
    GraphQLNonNull,
    GraphQLList,
    GraphQLObjectType,
)
from typing import Any

from cannula.schema import build_and_extend_schema
from cannula.types import Argument, FieldType
from cannula.codegen.parse_type import parse_graphql_type
from cannula.codegen.parse_args import (
    parse_field_arguments,
    parse_default_value,
)

SCHEMA = """\
type User {
    id: ID!
    name: String!
    count: Int
    active: Boolean
    score: Float
}
type Post {
    id: ID!
}
input CreateUser {
    name: String!
}
"""

mock_schema = build_and_extend_schema([SCHEMA])

# Mock types for testing
mock_types = {
    "User": GraphQLObjectType(
        name="User", fields={}, extensions={"py_type": "UserType"}
    ),
    "Post": GraphQLObjectType(
        name="Post", fields={}, extensions={"py_type": "PostType"}
    ),
    "CreateUser": GraphQLInputObjectType(
        name="CreateUser", fields={}, extensions={"py_type": "CreateUserInput"}
    ),
}


@pytest.mark.parametrize(
    "type_obj,expected",
    [
        pytest.param(GraphQLString, FieldType("str", False), id="string"),
        pytest.param(
            GraphQLNonNull(GraphQLString), FieldType("str", True), id="required-string"
        ),
        pytest.param(
            GraphQLList(GraphQLString),
            FieldType("Sequence[str]", False),
            id="string-list",
        ),
        pytest.param(
            GraphQLNonNull(GraphQLList(GraphQLString)),
            FieldType("Sequence[str]", True),
            id="required-string-list",
        ),
        pytest.param(
            mock_types["User"], FieldType("UserType", False), id="custom-type"
        ),
        pytest.param(
            GraphQLNonNull(mock_types["User"]),
            FieldType("UserType", True),
            id="required-custom-type",
        ),
        pytest.param(
            GraphQLList(mock_types["Post"]),
            FieldType("Sequence[PostType]", False),
            id="list-of-custom",
        ),
    ],
)
def test_parse_graphql_type(type_obj: Any, expected: FieldType):
    result = parse_graphql_type(type_obj, mock_schema.type_map)
    assert result == expected


@pytest.mark.parametrize(
    "field,expected_args",
    [
        pytest.param(
            GraphQLField(
                type_=GraphQLString,
                args={
                    "name": GraphQLArgument(
                        type_=GraphQLString,
                    )
                },
            ),
            [Argument(name="name", type="str", required=False)],
            id="simple-string-arg",
        ),
        pytest.param(
            GraphQLField(
                type_=GraphQLString,
                args={
                    "count": GraphQLArgument(
                        type_=GraphQLNonNull(GraphQLInt), default_value=42
                    )
                },
            ),
            [Argument(name="count", type="int", required=True, default=42)],
            id="required-int-with-default",
        ),
        pytest.param(
            GraphQLField(
                type_=GraphQLString,
                args={
                    "count": GraphQLArgument(
                        type_=GraphQLNonNull(GraphQLInt), default_value=None
                    )
                },
            ),
            [Argument(name="count", type="int", required=True, default=None)],
            id="required-default-none",
        ),
        pytest.param(
            GraphQLField(
                type_=GraphQLString,
                args={
                    "name": GraphQLArgument(type_=GraphQLString),
                    "active": GraphQLArgument(type_=GraphQLBoolean, default_value=True),
                    "score": GraphQLArgument(type_=GraphQLFloat, default_value=3.14),
                },
            ),
            [
                Argument(name="active", type="bool", required=False, default=True),
                Argument(name="name", type="str", required=False),
                Argument(name="score", type="float", required=False, default=3.14),
            ],
            id="multiple-args",
        ),
        pytest.param(
            GraphQLField(
                type_=GraphQLString,
                args={
                    "user": GraphQLArgument(
                        type_=GraphQLNonNull(mock_types["CreateUser"])
                    )
                },
            ),
            [Argument(name="user", type="CreateUserInput", required=True)],
            id="custom-type-arg",
        ),
        pytest.param(
            GraphQLField(
                type_=GraphQLString,
                args={
                    "tags": GraphQLArgument(
                        type_=GraphQLList(GraphQLString), default_value=["default"]
                    )
                },
            ),
            [
                Argument(
                    name="tags",
                    type="Sequence[str]",
                    required=False,
                    default=["default"],
                )
            ],
            id="list-arg",
        ),
    ],
)
def test_parse_field_arguments(field: GraphQLField, expected_args: list[Argument]):
    result = parse_field_arguments(field, mock_schema.type_map)
    assert result == expected_args


def create_field_with_default(
    schema_str: str, field_name: str = "testField"
) -> GraphQLField:
    """Helper to create a field with default value from schema string"""
    schema = build_and_extend_schema([schema_str])
    return schema.type_map["Query"].fields[field_name]  # type: ignore


@pytest.mark.parametrize(
    "schema,expected_default",
    [
        pytest.param(
            """
            type Query {
                testField(arg: String = "default"): String
            }
            """,
            "default",
            id="string-default",
        ),
        pytest.param(
            """
            type Query {
                testField(arg: Int = 42): String
            }
            """,
            42,
            id="int-default",
        ),
        pytest.param(
            """
            type Query {
                testField(arg: Float = 3.14): String
            }
            """,
            3.14,
            id="float-default",
        ),
        pytest.param(
            """
            type Query {
                testField(arg: Boolean = true): String
            }
            """,
            True,
            id="boolean-default",
        ),
        pytest.param(
            """
            type Query {
                testField(arg: [String] = ["a", "b"]): String
            }
            """,
            ["a", "b"],
            id="list-default",
        ),
        pytest.param(
            """
            type Query {
                testField(arg: [Int] = [23, 56]): Int
            }
            """,
            [23, 56],
            id="list-ints",
        ),
        pytest.param(
            """
            enum Status { ACTIVE INACTIVE }
            type Query {
                testField(arg: Status = ACTIVE): String
            }
            """,
            "ACTIVE",
            id="enum-default",
        ),
        pytest.param(
            """
            input Point {
                x: Int
                y: Int
            }
            type Query {
                testField(arg: Point = {x: 1, y: 2}): String
            }
            """,
            {"x": 1, "y": 2},
            id="input-object-default",
        ),
    ],
)
def test_parse_default_value(schema: str, expected_default: Any):
    _schema = build_and_extend_schema([schema])
    field = _schema.type_map["Query"].fields["testField"]  # type: ignore
    arg = field.args["arg"]
    field_type = parse_graphql_type(arg.type, _schema.type_map)
    result = parse_default_value(arg, field_type.value or "Any")
    assert result == expected_default


def test_parse_default_no_ast_node():
    """Test handling of arguments without AST nodes"""
    arg = GraphQLArgument(
        type_=GraphQLString,
    )
    result = parse_default_value(arg, "str")
    assert result is None


def test_parse_default_invalid_ast():
    """Test handling of invalid default values"""
    schema_str = """
    type Query {
        testField(arg: Int = "not a number"): String
    }
    """
    field = create_field_with_default(schema_str)
    arg = field.args["arg"]
    result = parse_default_value(arg, "int")
    assert result is None
