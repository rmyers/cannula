from typing import Annotated

from cannula.contrib.asgi import GraphQLDepends, ExecutionResponse, GraphQLExec
from fastapi import APIRouter, Depends

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
) -> ExecutionResponse:
    context = Context(config.session)
    return await graph_call(context=context)
