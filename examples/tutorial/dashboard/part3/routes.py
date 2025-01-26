from typing import Annotated

from cannula.contrib.asgi import GraphQLDepends, ExecutionResponse, GraphQLExec
from fastapi import APIRouter, Depends

from dashboard.core.config import config
from .gql.context import Context
from .graph import cannula_app

part3 = APIRouter(prefix="/part3")


@part3.post("/graph")
async def part3_root(
    graph_call: Annotated[
        GraphQLExec,
        Depends(GraphQLDepends(cannula_app)),
    ],
) -> ExecutionResponse:
    # create a context instance for our resolvers to use
    context = Context(config.session)
    return await graph_call(context=context)
