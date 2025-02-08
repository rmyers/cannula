import dataclasses

from graphql import (
    ListTypeNode,
    NamedTypeNode,
    NonNullTypeNode,
    TypeNode,
    VariableDefinitionNode,
)


@dataclasses.dataclass
class Variable:
    name: str
    value: str
    required: bool
    is_list: bool

    def coerce_variable(self, variable):
        if self.value == "Int":
            return int(variable)
        elif self.value == "Float":
            return float(variable)
        elif self.value == "Boolean":
            return variable.lower() in ("true", "1", "yes")
        elif self.value == "ID":
            return str(variable)
        else:
            # Could extend this to handle custom scalars from schema
            return variable


def parse_variable(variable: VariableDefinitionNode) -> Variable:
    name = variable.variable.name.value
    return parse_variable_type(name, variable.type)


def parse_variable_type(
    name: str, type_node: TypeNode, required: bool = False, is_list: bool = False
) -> Variable:
    if isinstance(type_node, NonNullTypeNode):
        return parse_variable_type(name, type_node.type, required=True, is_list=is_list)

    if isinstance(type_node, ListTypeNode):
        return parse_variable_type(
            name, type_node.type, required=required, is_list=True
        )

    if isinstance(type_node, NamedTypeNode):
        return Variable(
            name=name,
            value=type_node.name.value,
            required=required,
            is_list=is_list,
        )

    raise AttributeError("unable to parse variable")
