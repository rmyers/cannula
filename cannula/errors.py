import logging
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
