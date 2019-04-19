"""
Debug Middleware
================

Use this middleware to log details about the queries that you are running.

By default this will use logging.debug and will use the cannula logger. You
can override that when you setup the middleware.

Example with Cannula API
------------------------

    import cannula
    from cannula.middleware import DebugMiddleware

    api = cannula.API(
        __name__,
        schema=SCHEMA,
        middleware=[
            DebugMiddleware(),
        ],
    )


Example with `graphql-core-next`
--------------------------------

You can optionally use this middleware as a standalone with the `graphql-core-next`

    from cannula.middleware import DebugMiddleware
    from graphql import graphql

    graphql(
        schema=SCHEMA,
        query=QUERY,
        middleware=[
            DebugMiddleware(),
        ],
    )

"""
import inspect
import logging


class DebugMiddleware:

    def __init__(self, level: int = logging.DEBUG, logger: logging.Logger = None):
        self.level = level
        self.logger = logger or logging.getLogger('cannula.middleware.debug')

    async def resolve(self, _next, _resource, _info, **kwargs):
        type_name = _info.parent_type.name  # schema type (Query, Mutation)
        field_name = _info.field_name  # The attribute being resolved
        return_type = _info.return_type  # The field type that is being returned.

        self.logger.log(
            self.level,
            f'Resolving {field_name} on {type_name} with type {return_type}'
        )

        if inspect.isawaitable(_next):
            results = await _next(_resource, _info, **kwargs)
        else:
            results = _next(_resource, _info, **kwargs)

        if inspect.isawaitable(results):
            results = await results

        self.logger.log(
            self.level,
            f'Field {field_name} on {type_name} resolved: {results}'
        )

        return results
