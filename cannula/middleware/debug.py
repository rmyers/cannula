"""
Debug Middleware
================

Use this middleware to log details about the queries that you are running.

By default this will use logging.debug and will use the cannula logger. You
can override that when you setup the middleware.

Example with Cannula API
------------------------

::

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

You can optionally use this middleware as a standalone with the `graphql-core-next`::

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
import time
import typing

from graphql import GraphQLObjectType, GraphQLResolveInfo


class DebugMiddleware:
    def __init__(self, logger: typing.Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger("cannula.middleware.debug")

    async def resolve(
        self,
        next_fn: typing.Callable[..., typing.Any],
        parent_object: GraphQLObjectType,
        info: GraphQLResolveInfo,
        **kwargs,
    ):
        parent_name = info.parent_type.name
        field_name = info.field_name
        return_type = info.return_type

        self.logger.debug(
            f"Resolving {parent_name}.{field_name} expecting type {return_type}"
        )

        start_time = time.perf_counter()

        results = next_fn(parent_object, info, **kwargs)

        if inspect.isawaitable(results):
            results = await results

        end_time = time.perf_counter()
        total_time = end_time - start_time
        self.logger.debug(
            f"Field {parent_name}.{field_name} resolved: {results!r} in {total_time:.6f} seconds"
        )

        return results
