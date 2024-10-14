from typing import Annotated

from cannula.contrib.asgi import GraphQLDepends, ExecutionResponse
from fastapi import APIRouter, Depends

from .graph import cannula_app

part3 = APIRouter(prefix="/part3")


@part3.post("/graph")
async def part3_root(
    graph_response: Annotated[ExecutionResponse, Depends(GraphQLDepends(cannula_app))]
) -> ExecutionResponse:
    return graph_response
