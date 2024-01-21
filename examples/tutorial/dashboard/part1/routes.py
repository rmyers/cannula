import pathlib

from fastapi import APIRouter, Request

import cannula
from cannula.contrib.asgi import GraphQLPayload

part1 = APIRouter(prefix="/part1")
cannula_app = cannula.API(schema=pathlib.Path("./"))


@part1.post("/graph")
async def graph(request: Request, payload: GraphQLPayload):
    results = await cannula_app.call(
        payload.query, request, variables=payload.variables
    )
    errors = [e.formatted for e in results.errors] if results.errors else None
    return {"data": results.data, "errors": errors}
