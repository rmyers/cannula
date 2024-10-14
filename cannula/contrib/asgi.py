import typing

import fastapi
import pydantic

import cannula


class GraphQLPayload(pydantic.BaseModel):
    """Model representing a GraphQL request body."""

    query: str
    variables: typing.Optional[typing.Dict[str, typing.Any]] = None
    operation: typing.Optional[str] = None


class ExecutionResponse(pydantic.BaseModel):
    data: typing.Optional[typing.Dict[str, typing.Any]] = None
    errors: typing.Optional[list] = None
    extensions: typing.Optional[typing.Dict[str, typing.Any]] = None


class GraphQLDepends:

    graph: cannula.API

    def __init__(self, graph: cannula.API) -> None:
        self.graph = graph

    async def __call__(
        self, request: fastapi.Request, payload: GraphQLPayload
    ) -> ExecutionResponse:
        results = await self.graph.call(
            payload.query, request, variables=payload.variables
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
