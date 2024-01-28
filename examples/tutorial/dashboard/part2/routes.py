from fastapi import APIRouter, Request

import cannula

from dashboard.core.config import config
from .graph import cannula_app

part2 = APIRouter(prefix="/part2")

QUERY = cannula.gql(
    """
    query LoggedInUser {
        me {
            id
            name
        }
    }
    """
)


@part2.get("/")
async def part2_root(request: Request):
    results = await cannula_app.call(QUERY, request)
    return config.templates.TemplateResponse(
        request, "part2/index.html", {"results": results}
    )
