import logging
import re
import typing

from pydantic import ValidationError

from graphql import GraphQLError, GraphQLFormattedError
from pydantic_core import ErrorDetails

DEFAULT_LOGGER = logging.getLogger(__name__)


def format_errors(
    errors: typing.Optional[typing.List[GraphQLError]] = None,
    logger: typing.Optional[logging.Logger] = None,
    level: int = logging.DEBUG,
) -> typing.Optional[typing.List[GraphQLFormattedError]]:
    """Return a dict object of the errors.

    If there is a path(s) in the error then return a dict with the path
    as a key so that it is easier on the client side code to display the
    error with the correct data.
    """
    if not errors:
        return None

    logger = logger or DEFAULT_LOGGER

    formatted_errors: typing.List[GraphQLFormattedError] = []

    for err in errors:
        log_error(err, logger, level)

        # Format the error before adding it to formatted_errors
        for error in parse_graphql_error(err):
            formatted_errors.append(error.formatted)

    return formatted_errors


def log_error(
    error: GraphQLError,
    logger: logging.Logger,
    level: int,
):
    if tb := error.__traceback__:
        while tb and tb.tb_next:
            tb = tb.tb_next
        logger.log(level, f"{error} \nContext={tb.tb_frame.f_locals!r}")
    else:
        logger.log(level, f"{error}")


class SchemaValidationError(Exception):
    """Raised when the GraphQL schema metadata is invalid for model generation."""

    pass


def enhance_graphql_error(
    field: str, message: str, error: GraphQLError
) -> GraphQLError:
    """
    Enhance a GraphQLError with user-friendly message and field information.

    Args:
        error: The original GraphQLError

    Returns:
        An enhanced GraphQLError with updated message and extensions
    """
    # Update the error's extensions
    if not hasattr(error, "extensions") or not error.extensions:
        error.extensions = {}

    error.extensions["field"] = field

    # Replace the original message with user-friendly one
    error.message = message

    return error


def parse_graphql_error(error: GraphQLError) -> list[GraphQLError]:
    """
    Parse GraphQL errors to extract field name and create user-friendly message

    Args:
        error: A GraphQL error

    Returns:
        A tuple of (field_path, user_friendly_message)
    """
    field = "general"
    message = error.message

    # Handle Pydantic validation errors
    if hasattr(error, "original_error") and error.original_error:
        original_error = error.original_error
        if isinstance(original_error, ValidationError):
            errors = original_error.errors()
            return [parse_pydantic_error(err) for err in errors]

    # Handle standard GraphQL errors
    if error.message:
        # Extract field path from messages like:
        # "Variable '$input' got invalid value 'lskdj' at 'input.password';
        # Int cannot represent non-integer value: 'lskdj'"
        field_path_match = re.search(r"at ['\"]([^'\"]+)['\"]", error.message)
        if field_path_match:
            field = field_path_match.group(1)

            # Extract the field name from the path (e.g., 'input.password' -> 'password')
            field_parts = field.split(".")
            field_name = field_parts[-1] if len(field_parts) > 0 else "unknown"

            # Create a human-readable message based on error patterns
            if (
                "Int cannot represent" in error.message
                or "not a valid integer" in error.message
            ):
                message = f"Please enter a valid number for {field_name}"
            elif "String cannot represent" in error.message:
                message = f"Please enter valid text for {field_name}"
            elif "Boolean cannot represent" in error.message:
                message = f"Please provide a yes/no value for {field_name}"
            elif "required" in error.message.lower():
                message = f"{field_name} is required"
            elif "not a valid email" in error.message.lower():
                message = f"Please enter a valid email address for {field_name}"
            elif "Enum" in error.message and "does not have a value" in error.message:
                message = f"Please select a valid option for {field_name}"
            else:
                message = f"Invalid input for field: {field_name}"

            return [enhance_graphql_error(field, message, error)]

    return [error]


def parse_pydantic_error(error: ErrorDetails) -> GraphQLError:
    field = ".".join(str(loc) for loc in error.get("loc", [])) or "unknown"
    field_name = field.split(".")[-1] or "unknown"
    error_type = error.get("type", "unknown")
    match error_type:
        case e if e.startswith("int_"):
            message = f"Please enter a valid number for '{field_name}'"
        case _:
            message = f"Invalid input for '{field_name}'"

    return GraphQLError(
        message=message, extensions={"field": field, "error_type": error_type}
    )


def humanize_error_message(field: str, message: str) -> str:
    """
    Convert technical error messages to user-friendly format

    Args:
        field: The field name
        message: The original error message

    Returns:
        A user-friendly error message
    """
    field_str = str(field)

    # Common error patterns
    if any(
        pattern in message.lower()
        for pattern in ["non-integer", "not a valid integer", "int cannot represent"]
    ):
        return f"Please enter a valid number for {field_str}"

    if "required" in message.lower():
        return f"{field_str} is required"

    if "must match" in message.lower() or "pattern" in message.lower():
        return f"{field_str} format is invalid"

    if any(
        pattern in message.lower()
        for pattern in [
            "minimum",
            "maximum",
            "less than",
            "greater than",
            "not in range",
        ]
    ):
        return f"{field_str} is out of the allowed range"

    if any(
        pattern in message.lower()
        for pattern in [
            "must be longer",
            "must be shorter",
            "string_too_short",
            "string_too_long",
        ]
    ):
        return f"{field_str} length is invalid"

    if "not a valid email" in message.lower():
        return "Please enter a valid email address"

    # Default: capitalize first letter
    return message[0].upper() + message[1:] if message else "Invalid input"
