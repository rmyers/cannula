"""
Simple HTMX handler for Cannula that executes predefined GraphQL operations
"""

from __future__ import annotations

import dataclasses
import logging
import pathlib
from typing import Any, Dict, List, Optional, Set, TYPE_CHECKING
from urllib.parse import parse_qs

from graphql import (
    DocumentNode,
    FieldNode,
    FragmentDefinitionNode,
    FragmentSpreadNode,
    OperationDefinitionNode,
    SelectionSetNode,
)
from jinja2 import Environment, FileSystemLoader, TemplateNotFound, Undefined
from starlette.requests import Request
from starlette.responses import HTMLResponse
from cannula.codegen.parse_variables import parse_variable, Variable

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from cannula import CannulaAPI


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


class SilentUndefined(Undefined):
    def _fail_with_undefined_error(self, *args, **kwargs):
        return ""


class HTMXHandler:
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

    def _collect_fragments(
        self, selection_set: SelectionSetNode, fragments: Set[str]
    ) -> None:
        """Recursively collect fragment spreads from a selection set."""
        for selection in selection_set.selections:
            if isinstance(selection, FragmentSpreadNode):
                fragments.add(selection.name.value)
                # Also collect fragments from the fragment definition
                fragment_def = self.fragments.get(selection.name.value)
                if fragment_def and fragment_def.selection_set:
                    self._collect_fragments(fragment_def.selection_set, fragments)
            elif isinstance(selection, FieldNode) and selection.selection_set:
                self._collect_fragments(selection.selection_set, fragments)

    def _get_field_template(
        self, selection_set: SelectionSetNode, path: Optional[List[str]] = None
    ) -> str:
        """Generate template HTML for a selection set."""
        if path is None:
            path = []

        template_parts = []

        for selection in selection_set.selections:
            if isinstance(selection, FieldNode):
                field_path = path + [selection.name.value]
                field_access = "-".join(field_path)

                if selection.selection_set:
                    nested_template = self._get_field_template(
                        selection.selection_set, field_path
                    )
                    template_parts.append(
                        f'<ul class="{field_access}">\n'
                        f"    {nested_template}\n"
                        f"</ul>"
                    )
                else:
                    template_parts.append(
                        f'<li class="{field_access}">'
                        f'   <span class="header-{field_access}">{field_access}:</span> '
                        f"{{{{ item.{selection.name.value} }}}}"
                        f"</li>"
                    )

            elif isinstance(selection, FragmentSpreadNode):
                fragment = self.fragments.get(selection.name.value)
                if fragment:
                    fragment_template = self._get_field_template(
                        fragment.selection_set, path
                    )
                    template_parts.append(fragment_template)

        return "\n    ".join(template_parts)

    def _generate_htmx_template(self, query_node: OperationDefinitionNode) -> str:
        """Generate an HTMX template for a query."""
        query_name = query_node.name.value if query_node.name else "anonymous"

        # Get the main query field name (usually the first field in the query)
        main_field = next(
            (
                sel.name.value
                for sel in query_node.selection_set.selections
                if isinstance(sel, FieldNode)
            ),
            query_name,
        )

        # Generate the field template starting from the main query field
        field_template = self._get_field_template(query_node.selection_set)

        template = f"""
<div id="{query_name}-container">
    {{% for item in data.{main_field} %}}
    <ul class="item">
        {field_template}
    </ul>
    {{% endfor %}}
</div>
"""
        return template

    async def handle_request(self, request: Request) -> HTMLResponse:
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
            context={"request": request},
            request=request,
        )

        if result.errors:
            return HTMLResponse(f"GraphQL Error: {result.errors[0]}", status_code=500)

        # Render template with result data
        try:
            template = self.jinja_env.get_template(operation.template_path)
        except TemplateNotFound:
            generated = self._generate_htmx_template(operation.node)
            template = self.jinja_env.from_string(generated)

        html = template.render(
            data=result.data,
            variables=variables,
            operation=operation,
            request=request,
        )

        return HTMLResponse(html)
