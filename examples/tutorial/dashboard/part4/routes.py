from typing import Annotated

from cannula.contrib.asgi import GraphQLDepends, ExecutionResponse, GraphQLExec
from fastapi import APIRouter, Depends

from ..core.config import config
from .graph import cannula_app
from .gql.context import Context

part4 = APIRouter(prefix="/part4")


@part4.post("/graph")
async def part4_root(
    graph_call: Annotated[
        GraphQLExec,
        Depends(GraphQLDepends(cannula_app)),
    ],
) -> ExecutionResponse:
    context = Context(config.session)
    return await graph_call(context=context)
