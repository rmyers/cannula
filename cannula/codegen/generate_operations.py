from __future__ import annotations

import logging
import pathlib
from typing import Dict, List, Optional
from graphql import (
    DocumentNode,
    FieldNode,
    FragmentDefinitionNode,
    FragmentSpreadNode,
    OperationDefinitionNode,
    SelectionSetNode,
)
from jinja2 import Environment, FileSystemLoader

from cannula.codegen.schema_analyzer import SchemaAnalyzer, CodeGenerator
from cannula.codegen.parse_type import parse_graphql_type


logger = logging.getLogger(__name__)


class TemplateGenerator(CodeGenerator):
    """Generates Jinja templates for HTMX operations based on GraphQL schema"""

    def __init__(
        self,
        analyzer: SchemaAnalyzer,
        template_dir: str | pathlib.Path,
        jinja_env: Optional[Environment] = None,
        force: bool = False,
    ):
        super().__init__(analyzer)
        self.template_dir = pathlib.Path(template_dir)
        self.force = force
        self.jinja_env = jinja_env or Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=True,
        )
        self.fragments: Dict[str, FragmentDefinitionNode] = {}

    def _get_field_template(
        self,
        selection_set: SelectionSetNode,
        field_type: Optional[str] = None,
        path: Optional[List[str]] = None,
    ) -> str:
        """Generate template HTML for a selection set with type-specific markup."""
        if path is None:
            path = []

        template_parts = []

        for selection in selection_set.selections:
            if isinstance(selection, FieldNode):
                field_path = path + [selection.name.value]
                field_access = ".".join(field_path)
                field_name = " ".join(field_path[1:])

                # Get the field type from schema
                field_type = None
                print(selection.name.value)
                if selection.name.value in self.analyzer.schema.type_map:
                    field_type = parse_graphql_type(
                        self.analyzer.schema.type_map[selection.name.value]
                    ).value

                if selection.selection_set:
                    nested_template = self._get_field_template(
                        selection.selection_set, field_type, field_path
                    )
                    template_parts.append(
                        f'<div class="field-group {field_access}">\n'
                        f'    <h3 class="field-name">{field_name}</h3>\n'
                        f"    {nested_template}\n"
                        f"</div>"
                    )
                else:
                    # Add type-specific markup based on field_type
                    if field_type == "DateTime":
                        template_parts.append(
                            f'<div class="field {field_access}">\n'
                            f"    <label>{field_name}</label>\n"
                            f'    <sl-format-date date="{{{{ {field_access} }}}}"></sl-format-date>\n'
                            f"</div>"
                        )
                    elif field_type == "Float" or field_type == "Int":
                        template_parts.append(
                            f'<div class="field {field_access}">\n'
                            f"    <label>{field_name}</label>\n"
                            f'    <sl-format-number value="{{{{ {field_access} }}}}"></sl-format-number>\n'
                            f"</div>"
                        )
                    else:
                        template_parts.append(
                            f'<div class="field {field_access}">\n'
                            f"    <label>{field_name}</label>\n"
                            f'    <span class="value">{{{{ {field_access} }}}}</span>\n'
                            f"</div>"
                        )

            elif isinstance(selection, FragmentSpreadNode):
                fragment = self.fragments.get(selection.name.value)
                if fragment:
                    fragment_template = self._get_field_template(
                        fragment.selection_set, field_type, path
                    )
                    template_parts.append(fragment_template)

        return "\n    ".join(template_parts)

    def _generate_operation_template(self, operation: OperationDefinitionNode) -> str:
        """Generate a complete template for an operation."""
        operation_name = operation.name.value if operation.name else "anonymous"

        # Get the main query field name
        main_field = next(
            (
                sel.name.value
                for sel in operation.selection_set.selections
                if isinstance(sel, FieldNode)
            ),
            operation_name,
        )

        # Generate field template starting from main query field
        field_template = self._get_field_template(operation.selection_set)

        template = f"""
<div id="{operation_name}-container" class="operation-container">
    {{% for {main_field} in data.{main_field} %}}
    <div class="item">
        {field_template}
    </div>
    {{% endfor %}}
</div>
"""
        return template

    def generate(self, document: DocumentNode) -> None:
        """Generate templates for all operations in the document."""
        # First collect all fragments
        for definition in document.definitions:
            if isinstance(definition, FragmentDefinitionNode):
                self.fragments[definition.name.value] = definition

        # Generate templates for each operation
        for definition in document.definitions:
            if not isinstance(definition, OperationDefinitionNode):
                continue

            if not definition.name:
                continue

            print(definition.to_dict())

            name = definition.name.value
            template_content = self._generate_operation_template(definition)

            # Prepare template path
            template_path = self.template_dir / f"{name}.html"
            template_path.parent.mkdir(parents=True, exist_ok=True)

            # Check if file exists
            if template_path.exists() and not self.force:
                logger.warning(
                    f"Template '{name}.html' already exists. Use force=True to overwrite. Skipping..."
                )
                continue

            # Write template to file
            try:
                with open(template_path, "w") as f:
                    f.write(template_content)
                logger.info(f"Generated template: {template_path}")
            except IOError as e:
                logger.error(f"Failed to write template '{name}.html': {str(e)}")
