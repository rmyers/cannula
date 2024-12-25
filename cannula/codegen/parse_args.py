from typing import Any, Dict
from graphql import (
    DirectiveNode,
    GraphQLArgument,
    GraphQLField,
    GraphQLNamedType,
    Undefined,
)

from .parse_type import parse_argument_type, parse_graphql_type
from ..types import Argument


def parse_default_value(arg: GraphQLArgument, field_type: str) -> Any:
    """
    Parse the default value of an argument based on its type.
    Returns None if no default value is set.
    """
    if arg.default_value is None:
        return None

    if arg.default_value is Undefined:
        return None

    # GraphQL types map to Python types for default values
    type_map = {
        "bool": bool,
        "float": float,
        "int": int,
    }

    if value_func := type_map.get(field_type):
        return value_func(arg.default_value)

    # For other types, return the default value as is
    return arg.default_value


def parse_field_arguments(
    field: GraphQLField, schema_types: Dict[str, GraphQLNamedType]
) -> list[Argument]:
    """
    Parse a GraphQL field's arguments into Python argument definitions.

    Args:
        field: The GraphQL field whose arguments to parse
        schema_types: Dictionary of all types in the schema

    Returns:
        List of Argument objects representing the field's arguments
    """
    arguments: list[Argument] = []

    # Some fields might not have arguments
    if not field.args:
        return arguments

    for arg_name, arg in field.args.items():
        # Parse the argument type
        field_type = parse_graphql_type(arg.type, schema_types)

        # Get the default value using GraphQL's parser
        default_value = parse_default_value(arg, field_type.type)

        arguments.append(
            Argument(
                name=arg_name,
                type=field_type.value or "Any",  # Fallback to Any if no type
                value=None,  # GraphQL args don't have values, only defaults
                default=default_value,
                required=field_type.required,
            )
        )

    return sorted(arguments, key=lambda x: x.name)


def parse_directive_arguments(
    directive: DirectiveNode, schema_types: Dict[str, GraphQLNamedType]
) -> list[Argument]:
    """
    Parse a GraphQL Directive's arguments into Python argument definitions.

    Args:
        directive: The GraphQL directive whose arguments to parse
        schema_types: Dictionary of all types in the schema

    Returns:
        List of Argument objects representing the directives's arguments
    """
    arguments: list[Argument] = []

    # Some fields might not have arguments
    if not directive.arguments:
        return arguments

    for arg in directive.arguments:
        # Parse the argument type
        field_type = parse_argument_type(arg, schema_types)

        print(dir(arg))
        # Get the default value using GraphQL's parser
        default_value = parse_default_value(arg, field_type.type)

        arguments.append(
            Argument(
                name=arg.name.value,
                type=field_type.value or "Any",  # Fallback to Any if no type
                value=None,  # GraphQL args don't have values, only defaults
                default=default_value,
                required=field_type.required,
            )
        )

    return arguments
