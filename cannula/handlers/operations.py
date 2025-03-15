"""
Simple HTMX handler for Cannula that executes predefined GraphQL operations
"""

from __future__ import annotations

import dataclasses
import logging
import pathlib
from typing import Any, Dict, Optional
from urllib.parse import parse_qs

from graphql import (
    DocumentNode,
    FragmentDefinitionNode,
    OperationDefinitionNode,
)
from jinja2 import Environment, FileSystemLoader, Undefined
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse

from cannula import CannulaAPI
from cannula.codegen.parse_variables import parse_variable, Variable
from cannula.errors import format_errors

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class Operation:
    """Represents a parsed GraphQL operation with its metadata"""

    name: str
    operation_type: str  # 'query' or 'mutation'
    variable_types: Dict[str, Variable]
    node: OperationDefinitionNode

    @property
    def template_path(self) -> str:
        return f"{self.name}.html"


# TODO(rmyers): make this used by default and add tests
class SilentUndefined(Undefined):
    def _fail_with_undefined_error(self, *args, **kwargs):  # pragma: no cover
        return ""


# TODO(rmyers): refactor and add tests
class HTMXHandler:  # pragma: no cover
    """Handles HTMX requests with type coercion"""

    def __init__(
        self,
        api: "CannulaAPI",
        template_dir: str | pathlib.Path,
        jinja_env: Optional[Environment] = None,
    ):
        self.api = api
        self.template_dir = pathlib.Path(template_dir)
        self.jinja_env = jinja_env or Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=True,
            undefined=SilentUndefined,
        )
        self.operations: Dict[str, Operation] = {}
        self.fragments: Dict[str, FragmentDefinitionNode] = {}
        if api.operations is not None:
            self.operations = self.parse_operations(api.operations)

    def parse_operations(self, document: DocumentNode) -> Dict[str, Operation]:
        """Parse operations and their variable types"""

        # First pass: collect all fragments
        for definition in document.definitions:
            if isinstance(definition, FragmentDefinitionNode):
                self.fragments[definition.name.value] = definition

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
                variable_types=variables,
                node=definition,
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

    async def handle_request(self, request: Request) -> HTMLResponse | JSONResponse:
        """Handle incoming HTMX request"""
        name = request.path_params["name"]

        operation = self.operations.get(name)
        if not operation:
            return HTMLResponse(f"Operation '{name}' not found", status_code=404)

        # Parse query parameters and coerce types
        query_params = parse_qs(request.url.query)
        raw_variables = {
            name: query_params[name][0]
            for name in operation.variable_types
            if name in query_params
        }

        # Use schema analyzer to coerce variables
        variables = self.coerce_variables(operation, raw_variables)

        # Check for missing required variables
        missing = []
        for var_name, var in operation.variable_types.items():
            if var.required and var_name not in variables:
                missing.append(var_name)

        if missing:
            return HTMLResponse(
                f"Missing required variables: {', '.join(missing)}", status_code=400
            )

        # Execute GraphQL operation
        result = await self.api.exec_operation(
            operation_name=operation.name,
            variables=variables,
            request=request,
        )

        # Render template with result data
        template = self.jinja_env.get_template(operation.template_path)

        html = template.render(
            data=result.data,
            variables=variables,
            operation=operation,
            request=request,
        )

        # Return json if the accept header is JSON. The cannula htmx
        # plugin will set this if it is enabled. For this case we send
        # the html in the 'extensions' key allowing us to enrich the response
        # with toast messages and debug information.
        if "application/json" in request.headers.get("accept", ""):
            extensions = result.extensions or {}
            extensions["html"] = html
            return JSONResponse(
                {
                    "data": result.data,
                    "errors": format_errors(
                        result.errors, self.api.logger, self.api.level
                    ),
                    "extensions": extensions,
                }
            )

        return HTMLResponse(html)
