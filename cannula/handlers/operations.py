"""
Simple HTMX handler for Cannula that executes predefined GraphQL operations
"""

from __future__ import annotations

import dataclasses
import logging
import pathlib
from typing import Any, Dict, Optional
from urllib.parse import parse_qs

from cannula.handlers.forms import parse_nested_form
from graphql import (
    DocumentNode,
    ExecutionResult,
    FragmentDefinitionNode,
    OperationDefinitionNode,
)
from jinja2 import Environment, FileSystemLoader, Template, Undefined
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
    def is_mutation(self) -> bool:
        return self.operation_type == "mutation"

    @property
    def template_path(self) -> str:
        template_type = "_form" if self.is_mutation else ""
        return f"{self.name}{template_type}.html"

    @property
    def mutation_result_template(self) -> str:
        return f"{self.name}_result.html"


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
        self.mutations: Dict[str, Operation] = {}
        self.fragments: Dict[str, FragmentDefinitionNode] = {}
        self.parse_operations(api.operations)

    def parse_operations(self, document: DocumentNode | None) -> None:
        """Parse operations and their variable types"""

        if document is None:
            return

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

            operation = Operation(
                name=name,
                operation_type=definition.operation.value,
                variable_types=variables,
                node=definition,
            )
            self.operations[name] = operation
            if operation.operation_type == "mutation":
                self.mutations[name] = operation

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

    async def handle_mutation(self, request: Request) -> HTMLResponse | JSONResponse:
        name = request.path_params["name"]

        operation = self.mutations.get(name)
        if not operation:
            return HTMLResponse(f"Mutation '{name}' not found", status_code=404)

        variables = await parse_nested_form(request)
        logger.info(variables)
        # Render template with result data
        template = self.jinja_env.get_template(operation.mutation_result_template)

        result = await self.api.exec_operation(
            operation_name=operation.name,
            variables=variables,
            request=request,
        )

        return self.render_template(request, operation, template, result)

    async def handle_request(self, request: Request) -> HTMLResponse | JSONResponse:
        """Handle incoming HTMX request"""
        name = request.path_params["name"]

        operation = self.operations.get(name)
        if not operation:
            return HTMLResponse(f"Operation '{name}' not found", status_code=404)

        template = self.jinja_env.get_template(operation.template_path)

        if operation.is_mutation:
            return HTMLResponse(template.render(request=request))

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
        return self.render_template(request, operation, template, result)

    def render_template(
        self,
        request: Request,
        operation: Operation,
        template: Template,
        result: ExecutionResult,
        formatted_errors: dict[str, Any] | None = None,
    ) -> HTMLResponse | JSONResponse:
        status_code = 200 if result.errors is None else 400
        # Render template with result data
        try:
            html = template.render(
                data=result.data,
                operation=operation,
                request=request,
            )
        except Exception:
            # TODO(rmyers) use a template here
            html = '<article class="error">Unable to process request</article>'

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
                },
                status_code=status_code,
            )

        return HTMLResponse(html, status_code=status_code)
