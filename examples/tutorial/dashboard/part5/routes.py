from typing import Annotated

from cannula.contrib.asgi import GraphQLDepends, ExecutionResponse, GraphQLExec
from fastapi import APIRouter, Depends, Request

from ..core.config import config
from .graph import cannula_app
from .context import Context

part5 = APIRouter(prefix="/part5")


@part5.post("/graph")
async def part5_root(
    graph_call: Annotated[
        GraphQLExec,
        Depends(GraphQLDepends(cannula_app)),
    ],
    request: Request,
) -> ExecutionResponse:
    # We could also add a dependency for db_session but this we want to
    # show how this is working.
    async with config.session() as session:
        # Setup the context for all the resolvers
        context = Context(session, request)
        return await graph_call(context=context)
