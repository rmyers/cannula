from typing import cast
from graphql import (
    GraphQLType,
    GraphQLNonNull,
    GraphQLList,
    get_named_type,
    is_non_null_type,
    is_list_type,
    is_object_type,
)

from cannula.types import FieldType


def parse_graphql_type(
    type_obj: GraphQLType,
) -> FieldType:
    """
    Parse a GraphQL type into a Python type reference.

    Args:
        type_obj: The GraphQL type to parse
        schema_types: Dictionary of all types in the schema

    Returns:
        FieldType with the Python type name and whether it's required
    """
    if is_non_null_type(type_obj):
        non_null_type = cast(GraphQLNonNull, type_obj)
        inner = parse_graphql_type(non_null_type.of_type)
        return FieldType(
            value=inner.value,
            required=True,
            of_type=inner.of_type,
            is_list=inner.is_list,
            is_object_type=inner.is_object_type,
        )

    if is_list_type(type_obj):
        list_type = cast(GraphQLList, type_obj)
        inner = parse_graphql_type(list_type.of_type)
        return FieldType(
            value=f"Sequence[{inner.value}]",
            required=False,
            of_type=inner.of_type,
            is_list=True,
            is_object_type=inner.is_object_type,
        )

    # At this point we have a named type
    named_type = get_named_type(type_obj)
    type_name = named_type.extensions.get("py_type", named_type.name)

    return FieldType(
        value=type_name,
        required=False,
        of_type=type_name,
        is_object_type=is_object_type(named_type),
    )
