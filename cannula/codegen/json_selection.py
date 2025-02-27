"""
JSON Selection Parser and Mapper for Apollo Connect
================================================

Handles parsing of JSONPath-like selection strings and mapping JSON responses
to GraphQL fields.
"""

import re
from typing import Any, Dict, List, Union
from dataclasses import dataclass
import httpx

AnyDict = Dict[Any, Any]
Response = Union[List[AnyDict], AnyDict, httpx.Response]


@dataclass
class SelectionPath:
    """Represents a parsed JSON selection path"""

    root: str  # Root path (e.g., '$.products' or just 'products')
    fields: List[str]  # Fields to select
    is_array: bool = False  # Whether the selection is for an array


class JSONSelectionParser:
    """Parses JSONPath-like selection strings"""

    # Matches root paths like '$.products' or 'products'
    ROOT_PATH_PATTERN = r"^\$?\.?([^\s{]+)"

    # Matches field names in the selection
    FIELD_PATTERN = r"([a-zA-Z_][a-zA-Z0-9_]*)"

    @classmethod
    def parse(cls, selection: str) -> SelectionPath:
        """
        Parse a selection string into a SelectionPath object

        Examples:
            "$.products { id name }" -> SelectionPath(root="products", fields=["id", "name"])
            "products { id name }" -> SelectionPath(root="products", fields=["id", "name"])
            "{ id name }" -> SelectionPath(root="", fields=["id", "name"])
        """
        # Clean up the selection string
        selection = selection.strip()

        # Extract root path if present
        root_match = re.match(cls.ROOT_PATH_PATTERN, selection)
        root = root_match.group(1) if root_match else ""

        # Extract fields
        start_index = selection.find("{")
        fields_str = selection[start_index:].strip("{}").strip()
        fields = re.findall(cls.FIELD_PATTERN, fields_str)

        # Check if this is an array selection
        is_array = "[]" in selection or "[*]" in selection

        return SelectionPath(root=root, fields=fields, is_array=is_array)


class JSONResponseMapper:
    """Maps JSON responses according to selection paths"""

    @classmethod
    def get_value_at_path(cls, data: Any, path: str, default: Any = None) -> Any:
        """Get a value from nested JSON data using a dot-notation path"""
        if not path:
            return data

        current = data
        for key in path.split("."):
            if isinstance(current, dict):
                current = current.get(key, default)
            else:
                return default
        return current

    @classmethod
    def map_response(
        cls, response_data: Response, selection: SelectionPath
    ) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Map a JSON response according to the selection path

        Args:
            response_data: The JSON response data
            selection: The parsed selection path

        Returns:
            Mapped data according to the selection
        """
        # Get the data at the root path
        data = cls.get_value_at_path(response_data, selection.root, response_data)

        if selection.is_array:
            if not isinstance(data, list):
                data = [data] if data is not None else []

            # Map each item in the array
            return [
                {field: item.get(field) for field in selection.fields} for item in data
            ]
        else:
            # Map a single object
            return {field: data.get(field) for field in selection.fields}


def apply_selection(
    response_data: Response, selection: str
) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Apply a selection string to response data

    Args:
        response_data: The JSON response data
        selection: JSONPath-like selection string

    Example:
        >>> data = {"products": [{"id": 1, "name": "Product 1", "desc": "..."}]}
        >>> selection = "$.products { id name }"
        >>> apply_selection(data, selection)
        [{"id": 1, "name": "Product 1"}]
    """
    parsed = JSONSelectionParser.parse(selection)
    return JSONResponseMapper.map_response(response_data, parsed)
