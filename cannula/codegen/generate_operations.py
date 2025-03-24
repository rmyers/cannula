from __future__ import annotations

import logging
import pathlib
from typing import Dict, List, Optional
from cannula.codegen.macro_registry import TemplateMacros
from cannula.codegen.parse_variables import parse_variable
from cannula.types import InputType, ObjectType, Field, TemplateField
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


BASE_TEMPLATES_DIR = pathlib.Path(__file__).parent / "templates"


logger = logging.getLogger(__name__)


def get_field_by_name(object_type: ObjectType, field_name: str) -> Optional[Field]:
    """Get a field from an object type by name."""
    return next((f for f in object_type.fields if f.name == field_name), None)


def process_fragment(
    fragment: FragmentDefinitionNode,
    analyzer: SchemaAnalyzer,
    prefix: str,
    parent_type: ObjectType,
    fragments: Dict[str, FragmentDefinitionNode],
) -> List[TemplateField]:
    """Process a fragment and extract its fields."""
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
) -> List[TemplateField]:
    """
    Extract all fields from a selection set as TemplateField objects.

    Args:
        selection_set: GraphQL selection set to process
        analyzer: Schema analyzer instance
        prefix: Path prefix for fields
        parent_type: Parent object type
        fragments: Dictionary of fragments

    Returns:
        List of TemplateField objects
    """
    fields = []
    fragments = fragments or {}

    for selection in selection_set.selections:
        if isinstance(selection, FieldNode):
            field_name = selection.name.value
            field_path = f"{prefix}.{field_name}" if prefix else field_name
            schema_field = (
                get_field_by_name(parent_type, field_name) if parent_type else None
            )

            # If it has selections, process as a nested object
            if selection.selection_set and schema_field:
                nested_type_name = schema_field.field_type.of_type
                nested_type = analyzer.object_types_by_name.get(nested_type_name)

                if nested_type:
                    if schema_field.field_type.is_list:
                        # Create a list field with nested fields
                        nested_fields = get_fields_from_selection(
                            selection.selection_set,
                            analyzer,
                            "",  # Empty prefix for loop variables
                            nested_type,
                            fragments,
                        )

                        template_field = TemplateField.from_schema_field(
                            field_name=field_name,
                            path=field_name,  # Just the field name for loop var
                            schema_field=schema_field,
                        )
                        template_field.nested_fields = nested_fields
                        fields.append(template_field)
                    else:
                        logger.info(f"Here, {field_path} {field_name}")
                        # For regular objects, continue with the current path
                        nested_fields = get_fields_from_selection(
                            selection.selection_set,
                            analyzer,
                            field_path,
                            nested_type,
                            fragments,
                        )
                        fields.extend(nested_fields)
            else:
                logger.info(f"field {field_path} {field_name}")
                # Add a simple field
                fields.append(
                    TemplateField.from_schema_field(
                        field_name=field_name,
                        path=field_path,
                        schema_field=schema_field,
                    )
                )

        elif isinstance(selection, FragmentSpreadNode):
            fragment = fragments.get(selection.name.value)
            if fragment and parent_type:
                fragment_fields = process_fragment(
                    fragment, analyzer, prefix, parent_type, fragments
                )
                fields.extend(fragment_fields)

    return fields


def get_html_input_type(field: Field) -> str:
    """
    Determine the appropriate HTML input type based on the GraphQL field type.

    Args:
        field: Field object

    Returns:
        HTML input type string
    """
    field_type = field.field_type
    scalar_type = field_type.of_type.lower()
    field_name = field.name.lower()
    description = (field.description or "").lower()

    # First check for special fields based on name/description that override type
    if "password" in field_name or "password" in description:
        return "password"

    # Then prioritize scalar type mapping
    scalar_type_map = {
        # GraphQL default scalar types
        "int": "number",
        "float": "number",
        "string": "text",
        "boolean": "checkbox",
        "bool": "checkbox",
        "id": "text",
        # Extended scalar types (common in GraphQL schemas)
        "datetime": "datetime-local",
        "date": "date",
        "time": "time",
        "email": "email",
        "url": "url",
        "uuid": "text",
        "json": "textarea",
        "bigint": "number",
        "decimal": "number",
        "phone": "tel",
        "color": "color",
        "upload": "file",
        "longtext": "textarea",
        "richtext": "textarea",
    }

    # Check if we have a direct mapping for this scalar type
    if scalar_type in scalar_type_map:
        return scalar_type_map[scalar_type]

    # Next try matching field name patterns
    field_name_patterns = {
        "email": "email",
        "url": "url",
        "link": "url",
        "website": "url",
        "phone": "tel",
        "telephone": "tel",
        "mobile": "tel",
        "color": "color",
        "date": "date",
        "time": "time",
        "content": "textarea",
        "description": "textarea",
        "bio": "textarea",
        "about": "textarea",
        "notes": "textarea",
    }

    # Check if any pattern matches the field name
    for pattern, input_type in field_name_patterns.items():
        if pattern in field_name:
            return input_type

    # Check description for potential select/enum indication
    if "select" in description or "enum" in description or "options" in description:
        return "select"

    # Default to text input
    return "text"


def parse_field_type_to_html_attributes(field: Field) -> Dict[str, str]:
    """
    Convert field type constraints to HTML attributes.

    Args:
        field: GraphQL field

    Returns:
        Dictionary of HTML attributes
    """
    attributes = {}
    field_type = field.field_type
    scalar_type = field_type.of_type.lower()

    # Add required attribute if not nullable
    if field_type.required:
        attributes["required"] = ""

    # Add min/max for numeric types if constraints exist in directives or metadata
    if scalar_type in ["int", "float", "number"]:
        # You could extract min/max constraints from directives here
        # For example: if "min" in field.directives: attributes["min"] = field.directives["min"]
        pass

    return attributes


def field_to_label(field_name: str) -> str:
    """
    Convert a field name to a friendly label.

    Args:
        field_name: GraphQL field name

    Returns:
        Human-friendly label
    """
    return field_name.replace("_", " ").title()


def create_field_id(parent_name: str, field_name: str) -> str:
    """
    Create a valid HTML ID for a field.

    Args:
        parent_name: Parent object name
        field_name: Field name

    Returns:
        HTML-safe ID string
    """
    field_path = f"{parent_name}.{field_name}" if parent_name else field_name
    return field_path.replace(".", "_")


class TemplateGenerator(CodeGenerator):
    """Generates Jinja templates for HTMX operations based on GraphQL schema"""

    def __init__(
        self,
        analyzer: SchemaAnalyzer,
        template_dir: str | pathlib.Path,
        jinja_env: Optional[Environment] = None,
        force: bool = False,
        base_templates_dir: Optional[str | pathlib.Path] = None,
    ):
        super().__init__(analyzer)
        self.template_dir = pathlib.Path(template_dir)
        self.force = force
        self.fragments: Dict[str, FragmentDefinitionNode] = {}

        # Set up template loading
        self.base_templates_dir = (
            pathlib.Path(base_templates_dir)
            if base_templates_dir
            else BASE_TEMPLATES_DIR
        )
        self.base_templates_dir.mkdir(parents=True, exist_ok=True)

        # Initialize Jinja environment
        self.jinja_env = jinja_env or Environment(
            loader=FileSystemLoader(
                [str(self.template_dir), str(self.base_templates_dir)]
            ),
            autoescape=False,
        )

        # Create a mapping of input types by name for quick lookup
        self.input_types_by_name = {
            input_type.name: input_type for input_type in self.analyzer.input_types
        }

        # Ensure template macro files exist
        self._initialize_template_macros()

    def _initialize_template_macros(self) -> None:
        """Initialize template macro files if they don't exist."""
        # Here we would create the base template files if they don't exist
        # For simplicity, we'll just log a message for now
        self.macros = TemplateMacros(self.jinja_env)
        logger.info("Template macros should be placed in %s", self.base_templates_dir)

    def _render_field(
        self, field: Field, parent_name: str = "", is_required: bool = False
    ) -> str:
        """
        Render a field using the appropriate Jinja template.

        Args:
            field: Field object
            parent_name: Parent field name for nested objects
            is_required: Whether the field is required

        Returns:
            Rendered HTML for the form field
        """
        field_name = f"{parent_name}.{field.name}" if parent_name else field.name
        field_id = create_field_id(parent_name, field.name)
        label_text = field_to_label(field.name)
        input_type = get_html_input_type(field)
        help_text = field.description or ""

        template_name = None
        template_args = {
            "field_id": field_id,
            "field_name": field_name,
            "label_text": label_text,
            "help_text": help_text,
            "is_required": is_required,
        }

        if input_type == "textarea":
            template_name = "form_textarea"
        elif input_type == "checkbox":
            template_name = "form_checkbox"
        elif input_type == "select":
            template_name = "form_select"
            # This is a placeholder - in a real implementation, you'd need to
            # extract options from schema enums or field metadata
            template_args["options"] = [{"value": "", "label": "Select..."}]
        elif input_type == "number":
            template_name = "form_number"
        elif input_type in ["date", "datetime-local"]:
            template_name = "form_date"
            template_args["input_type"] = input_type
        else:
            template_name = "form_text_input"
            template_args["input_type"] = input_type

        # Render the template
        return getattr(self.macros, template_name)(**template_args)

    def _render_input_object_fields(
        self, input_type: InputType, parent_name: str = ""
    ) -> str:
        """
        Render all fields in an input object.

        Args:
            input_type: Input type object
            parent_name: Parent field name for nested objects

        Returns:
            Rendered HTML for form fields
        """
        fields_html = []

        for field in input_type.fields:
            field_name = f"{parent_name}.{field.name}" if parent_name else field.name
            is_required = field.field_type.required

            # Check if field is another input object
            if field.field_type.is_object_type:
                nested_type_name = field.field_type.of_type
                nested_type = self.input_types_by_name.get(nested_type_name)

                if nested_type:
                    # Render fieldset for nested object
                    nested_content = self._render_input_object_fields(
                        nested_type, field_name
                    )
                    fields_html.append(
                        self.macros.form_fieldset(input_type.name, nested_content)
                    )
                else:
                    # If type not found, render as regular field
                    fields_html.append(
                        self._render_field(field, parent_name, is_required)
                    )
            else:
                # Regular field
                fields_html.append(self._render_field(field, parent_name, is_required))

        return "\n".join(fields_html)

    def _generate_form_template(self, operation: OperationDefinitionNode) -> str:
        """
        Generate a form template for a mutation operation.

        Args:
            operation: The operation definition

        Returns:
            Complete HTML template for the form
        """
        operation_name = operation.name.value if operation.name else "anonymous"
        form_sections = []

        # Process each variable/argument
        for var_def in operation.variable_definitions:
            var_name = var_def.variable.name.value

            # Parse the variable type using schema analyzer's utility
            field_type = parse_variable(var_def)
            # is_required = field_type.required

            # Check if this is an input object type
            input_type = self.input_types_by_name.get(field_type.value)

            if input_type:
                # Render fieldset for input object
                fields_html = self._render_input_object_fields(input_type, var_name)
                form_sections.append(
                    self.macros.form_fieldset(field_type.name, fields_html)
                )
            else:
                logger.warning(
                    f"Input type {field_type.value} not found for variable {var_name}"
                )

        # Combine all sections
        form_content = "\n".join(form_sections)

        # Render the form template
        # template = self.jinja_env.get_template(self.TEMPLATE_PATHS["form_base"])
        return self.macros.form_container(operation_name, form_content)

    def _generate_operation_template(self, operation: OperationDefinitionNode) -> str:
        """
        Generate a template to display operation results.

        Args:
            operation: The operation definition

        Returns:
            Complete HTML template for displaying results
        """
        operation_name = operation.name.value if operation.name else "anonymous"

        # Process each top-level field in the result
        result_sections = []

        for selection in operation.selection_set.selections:
            if isinstance(selection, FieldNode):
                selection_name = selection.name.value
                selection_path = f"data.{selection_name}"

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

                    if object_type and selection.selection_set:

                        # Generate section for this field
                        fields = get_fields_from_selection(
                            selection.selection_set,
                            self.analyzer,
                            "",
                            object_type,
                            self.fragments,
                        )
                        if operation_field.field_type.is_list:

                            result_sections.append(
                                self.macros.result_list(
                                    selection_name, fields, selection_path
                                )
                            )
                        else:
                            result_sections.append(
                                self.macros.result_object(
                                    selection_name, fields, selection_path
                                )
                            )
                        print(result_sections)

        # Combine all sections
        result_content = "\n".join(result_sections)

        # Render the result template
        return self.macros.result_container(operation_name, result_content)

    def _write_file(self, template_path: pathlib.Path, content: str) -> None:
        if template_path.exists() and not self.force:
            logger.warning(
                f"Template '{template_path.name}' already exists. Use force=True to overwrite. Skipping..."
            )
            return

        # Write result template to file
        try:
            with open(template_path, "w") as f:
                f.write(content)
            logger.info(f"Generated result template: {template_path}")
        except IOError as e:
            logger.error(f"Failed to write template '{template_path.name}': {str(e)}")

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

                if definition.operation.value == "query":
                    template_content = self._generate_operation_template(definition)

                    # Prepare template path
                    template_path = self.template_dir / f"{name}.html"
                    template_path.parent.mkdir(parents=True, exist_ok=True)

                    self._write_file(template_path, template_content)

                elif definition.operation.value == "mutation":
                    # Generate form template
                    form_template_content = self._generate_form_template(definition)
                    form_template_path = self.template_dir / f"{name}_form.html"

                    # Generate result template
                    result_content = self._generate_operation_template(definition)
                    result_template_path = self.template_dir / f"{name}_result.html"

                    self._write_file(form_template_path, form_template_content)
                    self._write_file(result_template_path, result_content)
