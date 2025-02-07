"""
Simple HTMX handler for Cannula that executes predefined GraphQL operations
"""

from __future__ import annotations

import logging
import pathlib
from typing import Optional
from urllib.parse import parse_qs

from jinja2 import Environment, FileSystemLoader, Undefined
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse
from starlette.routing import Route
from cannula import CannulaAPI

from cannula.codegen.schema_analyzer import SchemaAnalyzer
from .operations import OperationAnalyzer

logger = logging.getLogger(__name__)


class SilentUndefined(Undefined):
    def _fail_with_undefined_error(self, *args, **kwargs):
        return ""


class HTMXHandler:
    """Handles HTMX requests with type coercion"""

    def __init__(
        self,
        api: CannulaAPI,
        schema_analyzer: SchemaAnalyzer,
        operations_file: str | pathlib.Path,
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

        # Initialize operation analyzer with schema
        self.operation_analyzer = OperationAnalyzer(schema_analyzer)

        # Parse operations
        with open(operations_file) as f:
            content = f.read()
        self.operations = self.operation_analyzer.parse_operations(content)
        print(self.operations)

    async def handle_request(self, request: Request) -> HTMLResponse:
        """Handle incoming HTMX request"""
        name = request.path_params["name"]

        operation = self.operation_analyzer.operations.get(name)
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
        variables = self.operation_analyzer.coerce_variables(operation, raw_variables)

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
        result = await self.api.call(
            operation.document,
            operation_name=operation.name,
            variables=variables,
            context={"request": request},
        )

        if result.errors:
            return HTMLResponse(f"GraphQL Error: {result.errors[0]}", status_code=500)

        # Render template with result data
        template = self.jinja_env.get_template(operation.template_path)
        html = template.render(data=result.data)

        return HTMLResponse(html)


def setup_htmx_app(
    api: CannulaAPI,
    schema_analyzer: SchemaAnalyzer,
    operations_file: str | pathlib.Path,
    template_dir: str | pathlib.Path,
) -> Starlette:
    """Create Starlette app with HTMX handler configured"""
    handler = HTMXHandler(api, schema_analyzer, operations_file, template_dir)
    return Starlette(routes=[Route("/operation/{name}", handler.handle_request)])
