import collections
import logging
import typing

from graphql import GraphQLError


def format_errors(
    errors: typing.Optional[typing.List[GraphQLError]] = None,
    logger: typing.Optional[logging.Logger] = None,
    level: int = logging.DEBUG,
) -> dict:
    """Return a dict object of the errors.

    If there is a path(s) in the error then return a dict with the path
    as a key so that it is easier on the client side code to display the
    error with the correct data.
    """
    if not errors:
        return {}

    if logger is None:
        logger = logging.getLogger(__name__)

    formatted_errors: typing.Dict[str, typing.List] = collections.defaultdict(list)

    for err in errors:
        log_error(err, logger, level)
        error_formatted = err.formatted
        error_message = error_formatted['message']
        if err.path is not None:
            for path in err.path:
                if error_message not in formatted_errors[path]:
                    formatted_errors[path].append(error_message)

        if error_message not in formatted_errors['errors']:
            formatted_errors['errors'].append(error_message)

    return formatted_errors


def log_error(
    error: GraphQLError,
    logger: logging.Logger,
    level: int,
):
    logger.log(level, f'{error}')
    tb = error.__traceback__
    while tb and tb.tb_next:
        tb = tb.tb_next
    logger.log(level, f'Excecution Context: {tb.tb_frame.f_locals!r}')
