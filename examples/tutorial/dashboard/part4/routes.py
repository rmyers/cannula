from typing import Annotated

from cannula.contrib.asgi import GraphQLDepends, ExecutionResponse, GraphQLExec
from fastapi import APIRouter, Depends, Request

from ..core.config import config
from .graph import cannula_app
from .context import Context

part4 = APIRouter(prefix="/part4")


@part4.post("/graph")
async def part4_root(
    graph_call: Annotated[
        GraphQLExec,
        Depends(GraphQLDepends(cannula_app)),
    ],
    request: Request,
) -> ExecutionResponse:
    context = Context(config.session, request)
    return await graph_call(context=context)
