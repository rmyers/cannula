from __future__ import annotations

import logging
import pathlib
from typing import Dict, List, Optional, Any
from cannula.types import ObjectType, Field
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


def create_field_info(
    field_name: str, path: str, field_obj: Optional[Field] = None
) -> Dict[str, Any]:
    """
    Create a field info dictionary with standardized attributes.

    Args:
        field_name: Name of the field
        path: Access path to the field
        field_obj: Optional Field object with type information

    Returns:
        Dictionary with field information
    """
    return {
        "path": path,
        "name": field_name,
        "label": field_name.replace("_", " ").title(),
        "type": field_obj.field_type.of_type if field_obj else "String",
        "is_list": field_obj.field_type.is_list if field_obj else False,
        "class_name": path.replace(".", "-"),
    }


def get_field_by_name(object_type: ObjectType, field_name: str) -> Optional[Field]:
    """
    Get a field from an object type by name.

    Args:
        object_type: The object type to search
        field_name: Name of the field to find

    Returns:
        Field object if found, None otherwise
    """
    return next((f for f in object_type.fields if f.name == field_name), None)


def process_fragment(
    fragment: FragmentDefinitionNode,
    analyzer: SchemaAnalyzer,
    prefix: str,
    parent_type: ObjectType,
    fragments: Dict[str, FragmentDefinitionNode],
) -> List[Dict[str, Any]]:
    """
    Process a fragment and extract its fields.

    Args:
        fragment: Fragment definition to process
        analyzer: Schema analyzer instance
        prefix: Path prefix for fields
        parent_type: Parent object type
        fragments: Dictionary of fragments

    Returns:
        List of field information dictionaries
    """
    if not fragment.type_condition:
        return []

    # Check if fragment applies to this type
    if fragment.type_condition.name.value != parent_type.name:
        return []

    return get_fields_from_selection(
        fragment.selection_set, analyzer, prefix, parent_type, fragments
    )


def get_fields_from_selection(
    selection_set: SelectionSetNode,
    analyzer: SchemaAnalyzer,
    prefix: str = "",
    parent_type: Optional[ObjectType] = None,
    fragments: Optional[Dict[str, FragmentDefinitionNode]] = None,
    flatten_nested_lists: bool = True,
) -> List[Dict[str, Any]]:
    """
    Extract all fields from a selection set, flattening nested objects.

    Args:
        selection_set: GraphQL selection set to process
        analyzer: Schema analyzer instance
        prefix: Path prefix for fields
        parent_type: Parent object type
        fragments: Dictionary of fragments
        flatten_nested_lists: Whether to flatten nested lists or keep them as objects

    Returns:
        List of field information dictionaries
    """
    fields = []
    fragments = fragments or {}

    for selection in selection_set.selections:
        if isinstance(selection, FieldNode):
            field_name = selection.name.value
            field_path = f"{prefix}.{field_name}" if prefix else field_name
            field_obj = (
                get_field_by_name(parent_type, field_name) if parent_type else None
            )

            # If it has selections, recurse into nested object
            if selection.selection_set and field_obj:
                nested_type_name = field_obj.field_type.of_type
                nested_type = analyzer.object_types_by_name.get(nested_type_name)

                if nested_type:
                    # Check if this is a list field - we need special handling
                    if field_obj.field_type.is_list:
                        if flatten_nested_lists:
                            # For lists, we want to generate a nested table, so we need to add the entire field
                            fields.append(
                                {
                                    "path": field_path,
                                    "name": field_name,
                                    "label": field_name.replace("_", " ").title(),
                                    "type": nested_type_name,
                                    "is_list": True,
                                    "class_name": field_path.replace(".", "-"),
                                    "nested_fields": get_fields_from_selection(
                                        selection.selection_set,
                                        analyzer,
                                        "",  # Reset prefix for nested fields
                                        nested_type,
                                        fragments,
                                    ),
                                }
                            )
                        else:
                            # We're not flattening, so just add the fields
                            nested_fields = get_fields_from_selection(
                                selection.selection_set,
                                analyzer,
                                field_path,
                                nested_type,
                                fragments,
                            )
                            fields.extend(nested_fields)
                    else:
                        # Regular object, continue flattening
                        nested_fields = get_fields_from_selection(
                            selection.selection_set,
                            analyzer,
                            field_path,
                            nested_type,
                            fragments,
                        )
                        fields.extend(nested_fields)
            else:
                # Add this field
                fields.append(create_field_info(field_name, field_path, field_obj))

        elif isinstance(selection, FragmentSpreadNode):
            fragment = fragments.get(selection.name.value)
            if fragment and parent_type:
                fragment_fields = process_fragment(
                    fragment, analyzer, prefix, parent_type, fragments
                )
                fields.extend(fragment_fields)

    return fields


def build_table_headers(fields: List[Dict[str, Any]]) -> List[str]:
    """
    Generate table header HTML for a set of fields.

    Args:
        fields: List of field information dictionaries

    Returns:
        List of HTML strings for table headers
    """
    headers = []
    for field in fields:
        headers.append(
            f'<th class="{field["class_name"]}-header">{field["label"]}</th>'
        )
    return headers


def build_table_cells(
    fields: List[Dict[str, Any]], item_var: str = "item"
) -> List[str]:
    """
    Generate table cell HTML for a set of fields.

    Args:
        fields: List of field information dictionaries
        item_var: Variable name to use for each item

    Returns:
        List of HTML strings for table cells
    """
    cells = []
    for field in fields:
        cells.append(
            f'<td class="{field["class_name"]}">{{{{{ item_var}.{field["path"]} }}}}</td>'
        )
    return cells


def build_nested_list_html(field: Dict[str, Any], parent_path: str) -> List[str]:
    """
    Build HTML for a nested list within an object.

    Args:
        field: Field information for the list
        parent_path: Path to the parent object

    Returns:
        List of HTML strings for the nested list
    """
    nested_fields = field.get("nested_fields", [])
    collection_path = f"{parent_path}.{field['path']}"
    field_label = field["label"]

    headers = build_table_headers(nested_fields)
    cells = build_table_cells(nested_fields)

    table_html = [
        f'<div class="nested-list {field["class_name"]}">',
        f"  <h3>{field_label}</h3>",
        "  <table>",
        "    <thead>",
        "      <tr>",
    ]

    # Add headers
    for header in headers:
        table_html.append(f"        {header}")

    table_html.extend(
        [
            "      </tr>",
            "    </thead>",
            "    <tbody>",
            f"      {{% for item in {collection_path} %}}",
            "      <tr>",
        ]
    )

    # Add cells
    for cell in cells:
        table_html.append(f"        {cell}")

    table_html.extend(
        ["      </tr>", "      {% endfor %}", "    </tbody>", "  </table>", "</div>"]
    )

    return table_html


def build_table_html(fields: List[Dict[str, Any]], collection_path: str) -> List[str]:
    """
    Build complete HTML table for a collection.

    Args:
        fields: List of field information dictionaries
        collection_path: Path to the collection

    Returns:
        List of HTML strings for the table
    """
    headers = build_table_headers(fields)
    cells = build_table_cells(fields)

    table_html = [
        '<div class="list-container">',
        "  <table>",
        "    <thead>",
        "      <tr>",
    ]

    # Add headers
    for header in headers:
        table_html.append(f"        {header}")

    table_html.extend(
        [
            "      </tr>",
            "    </thead>",
            "    <tbody>",
            f"      {{% for item in {collection_path} %}}",
            "      <tr>",
        ]
    )

    # Add cells
    for cell in cells:
        table_html.append(f"        {cell}")

    table_html.extend(
        ["      </tr>", "      {% endfor %}", "    </tbody>", "  </table>", "</div>"]
    )

    return table_html


def build_object_field_html(field: Dict[str, Any], context_path: str) -> str:
    """
    Build HTML for a single object field.

    Args:
        field: Field information dictionary
        context_path: Path to the parent object

    Returns:
        HTML string for the field
    """
    full_path = f"{context_path}.{field['path']}"
    return f'<dt>{field["label"]}</dt>\n' f"<dd>{{{{ {full_path} }}}}</dd>"


def build_definition_list(fields: List[Dict[str, Any]], context_path: str) -> List[str]:
    """
    Build HTML definition list for object fields.

    Args:
        fields: List of field information dictionaries
        context_path: Path to the parent object

    Returns:
        List of HTML strings for the definition list
    """
    dl_html = ["<dl>"]

    for field in fields:
        # Check if this is a nested list
        if field.get("is_list") and field.get("nested_fields"):
            # Add a nested list
            dl_html.extend(build_nested_list_html(field, context_path))
        else:
            # Add a regular field
            dl_html.append(build_object_field_html(field, context_path))

    dl_html.append("</dl>")
    return dl_html


def build_error_section() -> List[str]:
    """
    Build HTML for error handling section.

    Returns:
        List of HTML strings for the error section
    """
    return [
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

    def _generate_object_template(
        self,
        selection_set: SelectionSetNode,
        object_type: ObjectType,
        context_path: str,
    ) -> str:
        """
        Generate template HTML for a single object.

        Args:
            selection_set: GraphQL selection set
            object_type: Object type
            context_path: Path to this object in the context

        Returns:
            HTML string for the object
        """
        fields = get_fields_from_selection(
            selection_set, self.analyzer, "", object_type, self.fragments
        )

        dl_html = build_definition_list(fields, context_path)
        return "\n".join(dl_html)

    def _generate_list_template(
        self,
        selection_set: SelectionSetNode,
        object_type: ObjectType,
        context_path: str,
    ) -> str:
        """
        Generate template HTML for a list of objects.

        Args:
            selection_set: GraphQL selection set
            object_type: Object type of list items
            context_path: Path to the list in the context

        Returns:
            HTML string for the list
        """
        fields = get_fields_from_selection(
            selection_set, self.analyzer, "", object_type, self.fragments
        )

        table_html = build_table_html(fields, context_path)
        return "\n".join(table_html)

    def _generate_field_section(
        self, selection: FieldNode, operation_field: Field, object_type: ObjectType
    ) -> str:
        """
        Generate a section for a top-level field in an operation.

        Args:
            selection: Field node
            operation_field: Field information
            object_type: Object type for this field

        Returns:
            HTML string for the field section
        """
        selection_name = selection.name.value
        context_path = f"data.{selection_name}"
        field_label = selection_name.replace("_", " ").title()

        # Check if selection set exists
        if not selection.selection_set:
            # Return an empty placeholder for fields without selections
            return (
                f'<section class="{selection_name}-section">\n'
                f"  <h2>{field_label}</h2>\n"
                f'  <div class="empty-field">No fields selected</div>\n'
                f"</section>"
            )

        # Generate appropriate template based on field type
        if operation_field.field_type.is_list:
            content = self._generate_list_template(
                selection.selection_set, object_type, context_path
            )
        else:
            content = self._generate_object_template(
                selection.selection_set, object_type, context_path
            )

        # Wrap in section
        section_html = [
            f'<section class="{selection_name}-section">',
            f"  <h2>{field_label}</h2>",
            f"  {content}",
            "</section>",
        ]

        return "\n".join(section_html)

    def _generate_operation_template(self, operation: OperationDefinitionNode) -> str:
        """
        Generate a complete template for an operation.

        Args:
            operation: The operation definition

        Returns:
            Complete HTML template for the operation
        """
        operation_name = operation.name.value if operation.name else "anonymous"
        template_parts = []

        # Add error handling section
        error_section = build_error_section()
        template_parts.append("\n".join(error_section))

        # Process each top-level field
        for selection in operation.selection_set.selections:
            if isinstance(selection, FieldNode):
                selection_name = selection.name.value

                # Get field and type information
                operation_field = next(
                    (
                        f
                        for f in self.analyzer.operation_fields
                        if f.name == selection_name
                    ),
                    None,
                )

                if operation_field and operation_field.field_type.of_type:
                    object_type_name = operation_field.field_type.of_type
                    object_type = self.analyzer.object_types_by_name.get(
                        object_type_name
                    )

                    if object_type:
                        # Generate section for this field
                        section_html = self._generate_field_section(
                            selection, operation_field, object_type
                        )
                        template_parts.append(section_html)

        # Join all parts and wrap in container
        joined_content = "\n".join(template_parts)
        return f'<div class="{operation_name}">\n{joined_content}\n</div>'

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

        # Process all operations
        for definition in document.definitions:
            if isinstance(definition, OperationDefinitionNode):
                if not definition.name:
                    logger.warning("Skipping anonymous operation")
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
