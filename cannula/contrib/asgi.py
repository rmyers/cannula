import typing

import fastapi
import pydantic

import cannula


class GraphQLPayload(pydantic.BaseModel):
    """Model representing a GraphQL request body."""

    query: str
    variables: typing.Optional[typing.Dict[str, typing.Any]] = None
    operationName: typing.Optional[str] = None


class ExecutionResponse(pydantic.BaseModel):
    data: typing.Optional[typing.Dict[str, typing.Any]] = None
    errors: typing.Optional[list] = None
    extensions: typing.Optional[typing.Dict[str, typing.Any]] = None


class GraphQLExec(typing.Protocol):
    async def __call__(
        self,
        context: typing.Any | None = None,
    ) -> ExecutionResponse: ...


class GraphQLDepends:
    """
    FastAPI Dependency to handle GraphQL requests.

    Example::

        from fastapi import FastAPI
        from cannula import CannulaAPI
        from cannula.contrib.asgi import ExecutionResponse, GraphQLDepends, GraphQLExec

        api = FastAPI()
        cannula_app = API()

        @api.post("/graph")
        async def _root(
            graph_call: typing.Annotated[
                GraphQLExec,
                Depends(GraphQLDepends(cannula_app)),
            ]
        ) -> ExecutionResponse:
            return await graph_call()

    This function allows you to pass context or the request in order to handle complex
    operations. For example you can setup `data_loaders` or a database session::

        ...
        async with async_session_maker() as session:
            context = {
                'session': session,
                'authorization': request.headers.get('authoriztion')
            }
            return await graph_call(context=context)
    """

    graph: cannula.CannulaAPI

    def __init__(self, graph: cannula.CannulaAPI) -> None:
        self.graph = graph

    async def __call__(
        self, request: fastapi.Request, payload: GraphQLPayload
    ) -> GraphQLExec:

        async def _call_graph(
            context: typing.Any | None = None,
        ) -> ExecutionResponse:
            results = await self.graph.call(
                document=payload.query,
                variables=payload.variables,
                operation_name=payload.operationName,
                context=context,
                request=request,
            )

            return ExecutionResponse(
                data=results.data,
                errors=cannula.format_errors(
                    results.errors,
                    logger=self.graph.logger,
                    level=self.graph.level,
                ),
                extensions=results.extensions,
            )

        return _call_graph
