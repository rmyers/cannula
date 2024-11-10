import pathlib

from fastapi import APIRouter, Request

import cannula

from dashboard.core.config import config

part1 = APIRouter(prefix="/part1")
cannula_app = cannula.CannulaAPI(schema=pathlib.Path(config.root / "part1"))

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


@part1.get("/")
async def part1_root(request: Request):
    results = await cannula_app.call(QUERY)
    return config.templates.TemplateResponse(
        request, "part1/index.html", {"results": results}
    )
