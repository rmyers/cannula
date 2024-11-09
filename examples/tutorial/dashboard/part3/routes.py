from typing import Annotated

from cannula.contrib.asgi import GraphQLDepends, ExecutionResponse, GraphQLExec
from fastapi import APIRouter, Depends, Request

from ..core.config import config
from .graph import cannula_app
from .context import Context

part3 = APIRouter(prefix="/part3")


@part3.post("/graph")
async def part3_root(
    graph_call: Annotated[
        GraphQLExec,
        Depends(GraphQLDepends(cannula_app)),
    ],
    request: Request,
) -> ExecutionResponse:
    # create a context instance for our resolvers to use
    context = Context(config.session, request)
    return await graph_call(context=context)
