import logging
import typing

from graphql import (
    ListTypeNode,
    NamedTypeNode,
    NonNullTypeNode,
    TypeNode,
    Undefined,
    VariableDefinitionNode,
    value_from_ast_untyped,
)
from cannula.types import FieldType, Variable

LOG = logging.getLogger(__name__)


def parse_default_value(arg: VariableDefinitionNode) -> typing.Any:
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

    LOG.info(arg.default_value)
    LOG.info(arg.default_value.to_dict())

    if value_func := type_map.get(arg.type.kind):
        return value_func(arg.default_value)

    # For other types, return the default value as is
    return value_from_ast_untyped(arg.default_value)


def parse_variable(variable: VariableDefinitionNode) -> Variable:
    name = variable.variable.name.value
    default = parse_default_value(variable)
    _type = parse_graphql_type(variable.type)
    return Variable(
        name=name,
        value=_type.value,
        required=_type.required,
        is_list=_type.is_list,
        default=default,
    )


def parse_graphql_type(
    type_node: TypeNode,
) -> FieldType:
    """
    Parse a GraphQL type into a Python type reference.

    Args:
        type_obj: The GraphQL type to parse
        schema_types: Dictionary of all types in the schema

    Returns:
        FieldType with the Python type name and whether it's required
    """
    if isinstance(type_node, NonNullTypeNode):
        inner = parse_graphql_type(type_node.type)
        return FieldType(
            value=inner.value,
            required=True,
            of_type=inner.of_type,
            is_list=inner.is_list,
            is_object_type=inner.is_object_type,
        )

    if isinstance(type_node, ListTypeNode):
        inner = parse_graphql_type(type_node.type)
        return FieldType(
            value=inner.value,
            required=False,
            of_type=inner.of_type,
            is_list=True,
            is_object_type=inner.is_object_type,
        )

    if isinstance(type_node, NamedTypeNode):
        return FieldType(
            value=type_node.name.value,
        )

    raise AttributeError("unable to parse variable")
