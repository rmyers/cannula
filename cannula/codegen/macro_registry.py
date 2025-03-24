from __future__ import annotations

from functools import lru_cache
from typing import Optional, Callable, TypeVar

from jinja2 import Environment, Template

from cannula.types import TemplateField

# Type for macro return value
T = TypeVar("T")


class TemplateMacros:
    """
    A class that provides statically-typed access to Jinja template macros.

    Template files must be named to match the method names and should contain
    a macro with a matching name.

    Example usage:
        macros = TemplateMacros(jinja_env)
        html = macros.form_text_input(field_id="email", label_text="Email", is_required=True)
    """

    def __init__(
        self,
        jinja_env: Environment,
        base_path: str = "_macros",
    ):
        """
        Initialize the template macro registry.

        Args:
            jinja_env: Jinja environment for loading templates
            base_path: Base path for template files
        """
        self.jinja_env = jinja_env
        self.base_path = base_path

    @lru_cache(maxsize=128)
    def _get_template(self, name: str) -> Template:
        """Get a template by name with caching."""
        template_path = f"{self.base_path}/{name}.html"
        return self.jinja_env.get_template(template_path)

    @lru_cache(maxsize=128)
    def _get_macro(self, name: str) -> Callable:
        """Get a macro by name from its corresponding template with caching."""
        template = self._get_template(name)
        return getattr(template.module, name)

    def form_container(
        self,
        operation_name: str,
        form_content: str,
    ) -> str:
        """Renders a form container."""
        macro = self._get_macro("form_container")
        return macro(operation_name, form_content)

    def form_fieldset(
        self,
        label: str,
        content: str,
    ) -> str:
        """Renders a fieldset for grouping related form elements."""
        macro = self._get_macro("form_fieldset")
        return macro(label, content)

    def form_text_input(
        self,
        field_id: str,
        field_name: str,
        label_text: str,
        input_type: str,
        help_text: str,
        is_required: bool,
    ) -> str:
        """Renders a text input field."""
        macro = self._get_macro("form_text_input")
        return macro(
            field_id,
            field_name,
            label_text,
            input_type,
            help_text,
            is_required,
        )

    def form_textarea(
        self,
        field_id: str,
        field_name: str,
        label_text: str,
        help_text: str,
        is_required: bool,
    ) -> str:
        """Renders a textarea for multiline text input."""
        macro = self._get_macro("form_textarea")
        return macro(
            field_id,
            field_name,
            label_text,
            help_text,
            is_required,
        )

    def form_checkbox(
        self,
        field_id: str,
        field_name: str,
        label_text: str,
        help_text: str,
        is_required: bool,
    ) -> str:
        """Renders a checkbox input."""
        macro = self._get_macro("form_checkbox")
        return macro(
            field_id,
            field_name,
            label_text,
            help_text,
            is_required,
        )

    def form_select(
        self,
        field_id: str,
        field_name: str,
        label_text: str,
        help_text: str,
        options: list,
        is_required: bool,
    ) -> str:
        """Renders a select dropdown."""
        macro = self._get_macro("form_select")
        return macro(
            field_id,
            field_name,
            label_text,
            help_text,
            options,
            is_required,
        )

    def form_number(
        self,
        field_id: str,
        field_name: str,
        label_text: str,
        help_text: str,
        is_required: bool,
        min: Optional[float] = None,
        max: Optional[float] = None,
        step: Optional[float] = None,
    ) -> str:
        """Renders a number input."""
        macro = self._get_macro("form_number")
        return macro(
            field_id,
            field_name,
            label_text,
            help_text,
            is_required,
            min,
            max,
            step,
        )

    def form_date(
        self,
        field_id: str,
        field_name: str,
        label_text: str,
        help_text: str,
        is_required: bool,
        input_type: str,
    ) -> str:
        """Renders a date or datetime input."""
        macro = self._get_macro("form_date")
        return macro(
            field_id,
            field_name,
            label_text,
            help_text,
            is_required,
            input_type,
        )

    def result_container(
        self,
        operation_name: str,
        result_content: str,
    ) -> str:
        """Renders a container for operation results."""
        macro = self._get_macro("result_container")
        return macro(operation_name, result_content)

    def result_object(
        self,
        label: str,
        fields: list[TemplateField],
        data_path: str,
    ) -> str:
        """Renders an object result with proper handling of nested fields."""
        macro = self._get_macro("result_object")
        contents: list[str] = []

        for field in fields:
            # Check if this is a nested list field
            if field.is_list and field.nested_fields:
                # For nested lists, use the proper item name and field path
                item_name = field.name.lower()  # This is what we'll use in the for loop
                nested_path = f"{data_path}.{field.name}"  # Full path to the list

                # Generate a nested list with the appropriate loop variable and path
                contents.append(
                    self.result_list(item_name, field.nested_fields, nested_path)
                )
            else:
                # Add a regular field
                contents.append(self.result_object_item(label, field, data_path))

        content = "\n".join(contents)
        return macro(label, content, data_path)

    def result_list(
        self,
        label: str,
        fields: list[TemplateField],
        collection_path: str,
    ) -> str:
        """
        Renders a list of results with proper handling of nested lists.

        Args:
            label: The label for items in this list (used as loop variable)
            fields: The fields for each item in the list
            collection_path: The path to the collection (used in for loop statement)
        """
        macro = self._get_macro("result_list")
        contents: list[str] = []

        # Loop variable for the current level
        item_var = label.lower()

        for field in fields:
            # Check if this is a nested list
            if field.is_list and field.nested_fields:
                # For nested lists in a list item, we use the item_var as prefix
                nested_item_name = field.name.lower()
                nested_path = f"{item_var}.{field.name}"

                # Add a nested list with correct loop variable references
                contents.append(
                    self.result_list(nested_item_name, field.nested_fields, nested_path)
                )
            else:
                # Add a regular field, referencing the current loop variable
                contents.append(self.result_list_item(item_var, field, item_var))

        content = "\n".join(contents)
        return macro(label, content, collection_path)

    def result_object_item(
        self, label: str, field: TemplateField, data_path: str
    ) -> str:
        """Renders a single object field."""
        macro = self._get_macro("result_object_item")
        return macro(label, field, data_path)

    def result_list_item(self, label: str, field: TemplateField, item_path: str) -> str:
        """Renders a single list item field."""
        macro = self._get_macro("result_list_item")
        return macro(label, field, item_path)
