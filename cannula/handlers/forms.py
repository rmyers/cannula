import logging
import re
from typing import Dict, Any, Union

from starlette.requests import Request
from starlette.datastructures import FormData, UploadFile, QueryParams

LOG = logging.getLogger(__name__)


async def parse_nested_form(request: Request) -> Dict[str, Any]:
    """
    Parse a request and convert form data with dot notation into a nested structure.
    Works with both application/x-www-form-urlencoded and multipart/form-data.
    """
    # Use Starlette's built-in parser to get the form data
    form_data = await request.form()
    if not form_data:
        form_data = request.query_params

    LOG.info(form_data)
    # Process the form data into a nested structure
    return process_form_data(form_data)


def process_form_data(form_data: FormData | QueryParams) -> Dict[str, Any]:
    """Convert flat FormData with dot notation to nested structure"""
    result: Dict[str, Any] = {}

    for key, value in form_data.multi_items():
        # Handle keys with array or dot notation
        set_nested_value(result, key, value)

    return result


def set_nested_value(
    data: Dict[str, Any], key: str, value: Union[str, UploadFile]
) -> None:
    """Set a value in the nested structure based on the key notation"""
    # Check for array notation first
    array_match = re.match(r"([^\[]+)\[(\d+)\](.?)(.*)", key)

    if array_match:
        # Handle array notation
        array_name = array_match.group(1)
        index = int(array_match.group(2))
        separator = array_match.group(3)  # Will be '.' or empty
        remainder = array_match.group(4)

        # Handle case like 'company.departments[0].name'
        if "." in array_name:
            # Split the path before the array
            path_parts = array_name.split(".")
            array_name = path_parts[-1]  # Last part is the actual array name

            # Build the nested structure for the path before the array
            current = data
            for part in path_parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]

            # Now current points to the object that should contain the array
            if array_name not in current:
                current[array_name] = []

            # Ensure array has enough elements
            while len(current[array_name]) <= index:
                current[array_name].append({})

            # Set the value in the array
            if separator == "." and remainder:
                # Handle nested properties within array items
                set_nested_value(current[array_name][index], remainder, value)
            else:
                # Set the array item directly
                current[array_name][index] = value
        else:
            # Regular array notation without dots in the array name
            if array_name not in data:
                data[array_name] = []

            # Ensure the array is long enough
            while len(data[array_name]) <= index:
                data[array_name].append({})

            if separator == "." and remainder:
                # Handle nested properties within array items
                set_nested_value(data[array_name][index], remainder, value)
            else:
                # Set the array item directly
                data[array_name][index] = value
        return

    # Handle regular dot notation
    if "." in key:
        parts = key.split(".")
        current = data

        # Build the nested structure
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]

        # Set the value at the deepest level
        current[parts[-1]] = value
    else:
        # Handle regular fields (no dots)
        data[key] = value
