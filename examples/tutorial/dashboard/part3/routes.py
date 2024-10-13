import typing
from fastapi import APIRouter, Request

from cannula.contrib.asgi import GraphQLPayload, ExecutionResponse

from .graph import cannula_app

part3 = APIRouter(prefix="/part3")


@part3.post("/graph", response_model=ExecutionResponse)
async def part3_root(request: Request, payload: GraphQLPayload) -> typing.Any:
    results = await cannula_app.call(
        payload.query, request, variables=payload.variables
    )
    return results.formatted
