"""
Operation parser with schema-aware type coercion
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict
from graphql import (
    DocumentNode,
    OperationDefinitionNode,
    parse,
)

from cannula.codegen.parse_variables import parse_variable, Variable


@dataclass
class Operation:
    """Represents a parsed GraphQL operation with its metadata"""

    name: str
    operation_type: str  # 'query' or 'mutation'
    document: DocumentNode
    variable_types: Dict[str, Variable]  # Keep original GraphQL type nodes

    @property
    def template_path(self) -> str:
        return f"{self.name}.html"


class OperationAnalyzer:
    """Analyzes GraphQL operations with schema-aware type coercion"""

    def __init__(self):
        self.operations: Dict[str, Operation] = {}

    def parse_operations(self, operations_file: str) -> Dict[str, Operation]:
        """Parse operations and their variable types"""
        document = parse(operations_file)

        for definition in document.definitions:
            if not isinstance(definition, OperationDefinitionNode):
                continue

            if not definition.name:
                continue

            name = definition.name.value
            variables = {}

            # Store original TypeNodes for coercion
            for var_def in definition.variable_definitions or []:
                var_name = var_def.variable.name.value
                variables[var_name] = parse_variable(var_def)

            self.operations[name] = Operation(
                name=name,
                operation_type=definition.operation.value,
                document=document,
                variable_types=variables,
            )

        return self.operations

    def coerce_variables(
        self, operation: Operation, raw_variables: Dict[str, str]
    ) -> Dict[str, Any]:
        """Coerce all variables for an operation using schema types"""
        coerced = {}

        for var_name, raw_value in raw_variables.items():
            if var_name in operation.variable_types:
                type_node = operation.variable_types[var_name]
                coerced[var_name] = type_node.coerce_variable(raw_value)

        return coerced
