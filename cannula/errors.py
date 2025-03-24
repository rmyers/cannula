import dataclasses
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
        log_error(err, logger, level)
        formatted_errors.append(err.formatted)
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


@dataclasses.dataclass
class FormattedError:
    """Represents a user-friendly formatted error"""

    field: str
    message: str

    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary representation"""
        return {"field": self.field, "message": self.message}


def format_graphql_errors(error: GraphQLError | Exception) -> FormattedError:
    """
    Format GraphQL errors into human-readable messages

    Args:
        error: A GraphQL error or Exception

    Returns:
        A list of formatted errors with field names and user-friendly messages
    """
    if isinstance(error, GraphQLError):
        # Handle GraphQL validation errors
        if hasattr(error, "original_error") and error.original_error:
            return parse_validation_error(error.original_error)

        # Handle standard GraphQL errors
        if error.message:
            return parse_graphql_error_message(error.message)

    # Fallback for other errors
    return FormattedError(
        field="general",
        message=str(error) if error else "An unexpected error occurred",
    )


def parse_graphql_error_message(error_message: str) -> FormattedError:
    """
    Parse GraphQL error messages to extract field and create user-friendly message

    Args:
        error_message: The error message from GraphQL

    Returns:
        A list of formatted errors
    """
    # Extract field path from messages like:
    # "Variable '$input' got invalid value 'lskdj' at 'input.password'; Int cannot represent non-integer value: 'lskdj'"
    field_path_match = re.search(r"at ['\"]([^'\"]+)['\"]", error_message)
    field_path = field_path_match.group(1) if field_path_match else "unknown"

    # Extract the field name from the path (e.g., 'input.password' -> 'password')
    field_parts = field_path.split(".")
    field = field_parts[-1] if len(field_parts) > 0 else "unknown"

    # Create a human-readable message based on error patterns
    message = f"Invalid input for field: {field}"

    if (
        "Int cannot represent" in error_message
        or "not a valid integer" in error_message
    ):
        message = f"Please enter a valid number for {field}"
    elif "String cannot represent" in error_message:
        message = f"Please enter valid text for {field}"
    elif "Boolean cannot represent" in error_message:
        message = f"Please provide a yes/no value for {field}"
    elif "required" in error_message.lower():
        message = f"{field} is required"
    elif "not a valid email" in error_message.lower():
        message = f"Please enter a valid email address for {field}"
    elif "Enum" in error_message and "does not have a value" in error_message:
        message = f"Please select a valid option for {field}"

    return FormattedError(field=field_path, message=message)


def parse_validation_error(error: Exception) -> FormattedError:
    """
    Parse validation errors from various validation libraries

    Args:
        error: The validation error

    Returns:
        A list of formatted errors
    """
    # Handle Pydantic validation errors
    if hasattr(error, "errors") and callable(getattr(error, "errors", None)):
        return [
            FormattedError(
                field=".".join(str(loc) for loc in err.get("loc", [])[-1:]),
                message=humanize_error_message(
                    err.get("loc", [])[-1] if err.get("loc") else "unknown",
                    err.get("msg", ""),
                ),
            )
            for err in error.errors()  # type: ignore
        ]

    # Default error parsing
    error_str = str(error)
    return parse_graphql_error_message(error_str)


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
