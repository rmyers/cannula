import typing

import httpx
import pytest
from fastapi import Depends, FastAPI

import cannula
from cannula.contrib.asgi import GraphQLDepends, ExecutionResponse, GraphQLExec

QUERY = """
    query LoggedInUser {
        me {
            name
        }
    }
"""


@pytest.fixture()
async def cannula_app(valid_schema) -> cannula.CannulaAPI:
    async def resolve_me(*args, **kwargs) -> typing.Any:
        return {"name": "Tony Hawk"}

    async def resolve_you(*args, **kwargs) -> typing.Any:
        raise Exception("I am not working")

    cannula_app = cannula.CannulaAPI(
        schema=valid_schema,
        root_value={"me": resolve_me, "you": resolve_you},
    )
    return cannula_app


@pytest.fixture
async def graph_api(cannula_app) -> FastAPI:
    api = FastAPI()

    @api.post("/graph")
    async def _root(
        graph_response: typing.Annotated[
            GraphQLExec,
            Depends(GraphQLDepends(cannula_app)),
        ]
    ) -> ExecutionResponse:
        return await graph_response()

    return api


async def test_asgi_handlers(graph_api, valid_query_string):

    async with httpx.AsyncClient(
        base_url="http://testclient",
        transport=httpx.ASGITransport(app=graph_api),
    ) as client:
        response = await client.post("/graph", json={"query": valid_query_string})
        assert response.status_code == 200, response.text
        data = response.json()
        assert data.get("data") == {"me": {"name": "Tony Hawk"}}


async def test_asgi_handler_errors(graph_api):

    async with httpx.AsyncClient(
        base_url="http://testclient",
        transport=httpx.ASGITransport(app=graph_api),
    ) as client:
        response = await client.post(
            "/graph", json={"query": "query not_found { name }"}
        )
        assert response.status_code == 200, response.text
        assert response.json() == {
            "data": None,
            "errors": [
                {
                    "locations": [{"column": 19, "line": 1}],
                    "message": "Cannot query field 'name' on type 'Query'. Did you mean 'me'?",
                },
            ],
            "extensions": None,
        }


async def test_asgi_handler_data_with_errors(graph_api):

    async with httpx.AsyncClient(
        base_url="http://testclient",
        transport=httpx.ASGITransport(app=graph_api),
    ) as client:
        response = await client.post(
            "/graph", json={"query": "query Me { me { name } you { name }}"}
        )
        assert response.status_code == 200, response.text
        assert response.json() == {
            "data": {
                "me": {"name": "Tony Hawk"},
                "you": None,
            },
            "errors": [
                {
                    "locations": [{"column": 24, "line": 1}],
                    "message": "I am not working",
                    "path": ["you"],
                },
            ],
            "extensions": None,
        }
