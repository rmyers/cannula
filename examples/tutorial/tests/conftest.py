import dataclasses
import typing

import httpx
import pytest


from dashboard.main import app


@pytest.fixture
def client() -> httpx.AsyncClient:
    return httpx.AsyncClient(app=app, base_url="http://localhost")


@pytest.fixture
def graphql_path() -> str:
    return "/graph"


@dataclasses.dataclass
class GraphResponse:
    data: typing.Any = None
    errors: typing.Optional[typing.List[typing.Any]] = None


class GraphClient(typing.Protocol):
    def __call__(
        self, query: str, **variables: typing.Any
    ) -> typing.Awaitable[GraphResponse]:
        ...


@pytest.fixture
def graphql_client(client: httpx.AsyncClient, graphql_path: str) -> GraphClient:
    async def _client(query: str, **variables) -> GraphResponse:
        resp = await client.post(
            graphql_path,
            json={"query": query, "variables": variables},
        )
        assert resp.status_code == 200, resp.text
        return GraphResponse(**resp.json())

    return _client
