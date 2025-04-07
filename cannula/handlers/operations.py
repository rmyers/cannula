"""
Simple HTMX handler for Cannula that executes predefined GraphQL operations
"""

from __future__ import annotations

import logging
import pathlib
from typing import Any, Dict, Optional

from graphql import (
    ExecutionResult,
)
from jinja2 import Environment, FileSystemLoader, Template, Undefined
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse

from cannula import CannulaAPI
from cannula.errors import format_errors
from cannula.types import Operation

LOG = logging.getLogger(__name__)


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
        self.operations = api.operations
        self.mutations = api.mutations
        self.fragments = api.fragments

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

        # Render template with result data
        template = self.jinja_env.get_template(operation.mutation_result_template)

        result = await self.api.exec_operation(
            operation_name=operation.name,
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

        # Execute GraphQL operation
        result = await self.api.exec_operation(
            operation_name=operation.name,
            request=request,
        )
        return self.render_template(request, operation, template, result)

    def render_template(
        self,
        request: Request,
        operation: Operation,
        template: Template,
        result: ExecutionResult,
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
