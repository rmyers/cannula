from __future__ import annotations

import logging
import pathlib
from typing import Dict, List, Optional, Any, Tuple
from cannula.types import ObjectType, Field, FieldType
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


logger = logging.getLogger(__name__)


def get_flattened_fields(
    selection_set: SelectionSetNode,
    analyzer: SchemaAnalyzer,
    prefix: str = "",
    parent_type: Optional[ObjectType] = None,
) -> List[Dict[str, Any]]:
    """
    Recursively extract all fields from a selection set, flattening nested objects.

    Args:
        selection_set: GraphQL selection set to process
        analyzer: Schema analyzer instance to look up types
        prefix: Current path prefix for nested fields
        parent_type: Parent object type containing these fields

    Returns:
        List of dictionaries with field information
    """
    fields = []

    for selection in selection_set.selections:
        if isinstance(selection, FieldNode):
            field_name = selection.name.value
            field_path = f"{prefix}.{field_name}" if prefix else field_name

            # Get field from parent type
            field_type_info = None
            field_type_name = None
            if parent_type:
                field_obj = next(
                    (f for f in parent_type.fields if f.name == field_name), None
                )
                if field_obj:
                    field_type_info = field_obj.field_type
                    field_type_name = field_obj.field_type.of_type

            # If it has a selection set, it's a nested object
            if selection.selection_set:
                # Get the nested type
                nested_obj_type = None
                if field_type_name:
                    nested_obj_type = analyzer.object_types_by_name.get(field_type_name)

                # Recursively get nested fields
                if nested_obj_type:
                    nested_fields = get_flattened_fields(
                        selection.selection_set, analyzer, field_path, nested_obj_type
                    )
                    fields.extend(nested_fields)
            else:
                # It's a leaf field
                fields.append(
                    {
                        "path": field_path,
                        "name": field_name,
                        "type": (
                            field_type_info.of_type if field_type_info else "String"
                        ),
                        "is_list": (
                            field_type_info.is_list if field_type_info else False
                        ),
                    }
                )

        # Handle fragment spreads
        elif isinstance(selection, FragmentSpreadNode):
            # This would need to be implemented if fragments are needed
            pass

    return fields


def generate_table_html(
    fields: List[Dict[str, Any]], collection_path: str
) -> List[str]:
    """
    Generate HTML table markup for a collection of objects.

    Args:
        fields: List of field information dictionaries
        collection_path: The path to the collection in the template context

    Returns:
        List of HTML lines for the table
    """
    table_html = [
        f'<div class="list-container">',
        f"  <table>",
        f"    <thead>",
        f"      <tr>",
    ]

    # Add table headers
    for field in fields:
        path_parts = field["path"].split(".")
        header_text = path_parts[-1].replace("_", " ").title()
        class_name = field["path"].replace(".", "-")
        table_html.append(f'        <th class="{class_name}-header">{header_text}</th>')

    table_html.extend(
        [
            f"      </tr>",
            f"    </thead>",
            f"    <tbody>",
            f"      {{% for item in {collection_path} %}}",
            f"      <tr>",
        ]
    )

    # Add table cells for all fields
    for field in fields:
        path = field["path"]
        field_type = field["type"]
        class_name = path.replace(".", "-")

        # Format cell based on field type
        if field_type == "datetime":
            table_html.append(
                f'        <td class="{class_name}"><time datetime="{{{{ item.{path} }}}}">{{{{ item.{path} }}}}</time></td>'
            )
        else:
            table_html.append(
                f'        <td class="{class_name}">{{{{ item.{path} }}}}</td>'
            )

    table_html.extend(
        [
            f"      </tr>",
            f"      {{% endfor %}}",
            f"    </tbody>",
            f"  </table>",
            f"</div>",
        ]
    )

    return table_html


def generate_definition_list(
    fields: List[Dict[str, Any]], context_path: str, is_nested: bool = False
) -> List[str]:
    """
    Generate HTML definition list markup for object fields.

    Args:
        fields: List of field information dictionaries
        context_path: The path to the object in the template context
        is_nested: Whether this is a nested definition list

    Returns:
        List of HTML lines for the definition list
    """
    dl_html = []

    # Start with dl tag if this isn't a nested list (nested ones are wrapped by the caller)
    if not is_nested:
        dl_html.append("<dl>")

    for field in fields:
        field_name = field["name"]
        field_path = field["path"]
        field_type = field["type"]
        field_label = field_name.replace("_", " ").title()
        full_path = f"{context_path}.{field_path}"

        # Format based on field type
        if field_type == "datetime":
            dl_html.append(
                f"<dt>{field_label}</dt>\n"
                f'<dd><time datetime="{{{{ {full_path} }}}}">{{{{ {full_path} }}}}</time></dd>'
            )
        else:
            dl_html.append(
                f"<dt>{field_label}</dt>\n" f"<dd>{{{{ {full_path} }}}}</dd>"
            )

    # Close the dl tag if this isn't a nested list
    if not is_nested:
        dl_html.append("</dl>")

    return dl_html


def format_field_value(field_path: str, field_type: str) -> str:
    """
    Format a field value based on its type.

    Args:
        field_path: Full path to the field in the template context
        field_type: The type of the field

    Returns:
        Formatted HTML for the field value
    """
    if field_type == "datetime":
        return f'<time datetime="{{{{ {field_path} }}}}">{{{{ {field_path} }}}}</time>'
    else:
        return f"{{{{ {field_path} }}}}"


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

    def _process_field_node(
        self, selection: FieldNode, object_type: ObjectType, path: List[str]
    ) -> str:
        """
        Process a field node and generate appropriate HTML based on its type.

        Args:
            selection: The field node to process
            object_type: The parent object type
            path: Current path to this field

        Returns:
            HTML string for this field
        """
        selection_name = selection.name.value
        field_path = path + [selection_name]
        field_access = ".".join(field_path)
        field_label = selection_name.replace("_", " ").title()

        # Find field in the object type
        field = next((f for f in object_type.fields if f.name == selection_name), None)

        # If this field has selections, it's an object or list
        if selection.selection_set:
            # Get the field type information
            field_type_name = field.field_type.of_type if field else None
            nested_type = None

            if field_type_name:
                nested_type = self.analyzer.object_types_by_name.get(field_type_name)

            # If it's a list of objects, generate a table
            if field and field.field_type.is_list and nested_type:
                flattened_fields = get_flattened_fields(
                    selection.selection_set, self.analyzer, "", nested_type
                )

                table_html = generate_table_html(flattened_fields, field_access)
                return (
                    f'<div class="field-group {field_access}">\n'
                    + f"  <h3>{field_label}</h3>\n"
                    + f'  {"".join(table_html)}\n'
                    + f"</div>"
                )

            # If it's a single object, generate a definition list
            elif nested_type:
                flattened_fields = get_flattened_fields(
                    selection.selection_set, self.analyzer, "", nested_type
                )

                dl_html = generate_definition_list(flattened_fields, field_access)
                return (
                    f'<div class="field-group {field_access}">\n'
                    + f"  <h3>{field_label}</h3>\n"
                    + f'  {"".join(dl_html)}\n'
                    + f"</div>"
                )

            # Fallback for unknown object types
            else:
                return (
                    f'<div class="field {field_access}">\n'
                    + f"  <label>{field_label}</label>\n"
                    + f'  <span class="value">{{{{ {field_access} }}}}</span>\n'
                    + f"</div>"
                )

        # Simple scalar field
        else:
            field_type = "String"
            if field:
                field_type = field.field_type.of_type

            formatted_value = format_field_value(field_access, field_type)
            return (
                f'<div class="field {field_access}">\n'
                + f"  <label>{field_label}</label>\n"
                + f'  <span class="value">{formatted_value}</span>\n'
                + f"</div>"
            )

    def _get_field_template(
        self,
        selection_set: SelectionSetNode,
        object_type: ObjectType,
        path: Optional[List[str]] = None,
        is_root: bool = False,
    ) -> str:
        """
        Generate template HTML for a selection set.

        Args:
            selection_set: GraphQL selection set to process
            object_type: Parent object type
            path: Current path for nested fields
            is_root: Whether this is a root level object

        Returns:
            HTML string for the entire selection set
        """
        if path is None:
            path = []

        template_parts = []

        for selection in selection_set.selections:
            if isinstance(selection, FieldNode):
                html = self._process_field_node(selection, object_type, path)
                template_parts.append(html)

            # Handle fragment spreads
            elif isinstance(selection, FragmentSpreadNode):
                fragment = self.fragments.get(selection.name.value)
                if fragment:
                    fragment_template = self._get_field_template(
                        fragment.selection_set, object_type, path, is_root=is_root
                    )
                    template_parts.append(fragment_template)

        return "\n".join(template_parts)

    def _generate_operation_template(self, operation: OperationDefinitionNode) -> str:
        """
        Generate a complete template for an operation.

        Args:
            operation: The operation definition to process

        Returns:
            Complete HTML template for the operation
        """
        operation_name = operation.name.value if operation.name else "anonymous"

        template_parts = []

        # Add error handling section
        error_section = [
            '<div class="errors-section" hx-swap-oob="true" id="errors-container">',
            "  {% if errors %}",
            '  <div class="error-list">',
            "    {% for error in errors %}",
            '    <div class="error-item">{{ error.message }}</div>',
            "    {% endfor %}",
            "  </div>",
            "  {% endif %}",
            "</div>",
        ]
        template_parts.append("\n".join(error_section))

        for selection in operation.selection_set.selections:
            if isinstance(selection, FieldNode):
                selection_name = selection.name.value

                # Get operation field
                operation_field = next(
                    (
                        f
                        for f in self.analyzer.operation_fields
                        if f.name == selection.name.value
                    ),
                    None,
                )

                if operation_field and operation_field.field_type.of_type:
                    object_type_name = operation_field.field_type.of_type
                    object_type = self.analyzer.object_types_by_name.get(
                        object_type_name
                    )

                    if object_type and selection.selection_set:
                        # Check if the operation field is a list type (top-level collection)
                        if operation_field.field_type.is_list:
                            # Generate table for list of objects
                            flattened_fields = get_flattened_fields(
                                selection.selection_set, self.analyzer, "", object_type
                            )

                            table_html = generate_table_html(
                                flattened_fields, f"data.{selection_name}"
                            )
                            section_html = [
                                f'<section class="{selection_name}-section">',
                                f'  <h2>{selection_name.replace("_", " ").title()}</h2>',
                                f'  {"".join(table_html)}',
                                f"</section>",
                            ]

                            template_parts.append("\n".join(section_html))
                        else:
                            # Generate template for single object
                            field_template = self._get_field_template(
                                selection.selection_set,
                                object_type,
                                ["data", selection_name],
                                is_root=True,
                            )

                            section_html = [
                                f'<section class="{selection_name}-section">',
                                f'  <h2>{selection_name.replace("_", " ").title()}</h2>',
                                f"  {field_template}",
                                f"</section>",
                            ]

                            template_parts.append("\n".join(section_html))

        # Join the template parts first
        joined_parts = "\n".join(template_parts)

        # Then create the container div
        return f'<div class="{operation_name}">\n{joined_parts}\n</div>'

    def generate(self, document: DocumentNode) -> None:
        """
        Generate templates for all operations in the document.

        Args:
            document: GraphQL document to process
        """
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
            except IOError as e:  # pragma: no cover
                logger.error(f"Failed to write template '{name}.html': {str(e)}")
