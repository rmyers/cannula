import logging
import re
import typing

from graphql import GraphQLError, GraphQLFormattedError

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
        parsed = parse_graphql_error(err)
        # Only log errors that are unknown
        if not parsed.extensions:
            log_error(err, logger, level)

        formatted_errors.append(parsed.formatted)
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


def parse_graphql_error(error: GraphQLError) -> GraphQLError:
    """
    Parse GraphQL error messages to extract field and create user-friendly message

    Args:
        error_message: The error message from GraphQL

    Returns:
        A list of formatted errors
    """
    # Extract field path from messages like:
    # "Variable '$input' got invalid value 'lskdj' at 'input.password'; Int cannot represent non-integer value: 'lskdj'"
    field_path_match = re.search(r"at ['\"]([^'\"]+)['\"]", error.message)
    if not field_path_match:
        return error

    field_path = field_path_match.group(1)

    # Extract the field name from the path (e.g., 'input.password' -> 'password')
    field_parts = field_path.split(".")
    field = field_parts[-1] if len(field_parts) > 0 else "unknown"

    # Create a human-readable message based on error patterns
    message = f"Invalid input for field: {field}"

    if (
        "Int cannot represent" in error.message
        or "not a valid integer" in error.message
    ):
        message = f"Please enter a valid number for {field}"
    elif "String cannot represent" in error.message:
        message = f"Please enter valid text for {field}"
    elif "Boolean cannot represent" in error.message:
        message = f"Please provide a yes/no value for {field}"
    elif "required" in error.message.lower():
        message = f"{field} is required"
    elif "not a valid email" in error.message.lower():
        message = f"Please enter a valid email address for {field}"
    elif "Enum" in error.message and "does not have a value" in error.message:
        message = f"Please select a valid option for {field}"

    error.extensions = {"field": field_path, "original_error": error.message}
    error.message = message
    return error
