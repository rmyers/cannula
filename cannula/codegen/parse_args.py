from typing import Any, Dict, List, cast
from graphql import (
    GraphQLArgument,
    GraphQLField,
    GraphQLInputObjectType,
    GraphQLInterfaceType,
    GraphQLObjectType,
    Undefined,
)

from cannula.codegen.parse_type import parse_graphql_type
from cannula.errors import SchemaValidationError
from cannula.types import Argument


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


def parse_field_arguments(field: GraphQLField) -> list[Argument]:
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
    if not hasattr(field, "args") or not field.args:
        return arguments

    for arg_name, arg in field.args.items():
        # Parse the argument type
        field_type = parse_graphql_type(arg.type)

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


def parse_related_args(
    field: str,
    field_metadata: Dict[str, Any],
    parent: GraphQLObjectType | GraphQLInputObjectType | GraphQLInterfaceType,
) -> List[Argument]:
    related_args: list[Argument] = []
    metadata_args = field_metadata.get("args", [])
    if isinstance(metadata_args, str):
        metadata_args = metadata_args.split(",")

    for arg in metadata_args:
        arg_field = cast(GraphQLField, parent.fields.get(arg))
        if arg_field is None:
            raise SchemaValidationError(
                f"Field {field} Metadata Arg: {arg} not found on {parent.name}"
            )
        arg_type = parse_graphql_type(arg_field.type)
        related_args.append(Argument(arg, type=arg_type, required=True))
    return related_args
