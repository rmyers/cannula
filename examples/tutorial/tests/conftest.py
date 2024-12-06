import dataclasses
import logging
import typing

import httpx
import pytest


from dashboard.main import app
from dashboard.core.config import config
from dashboard.core.database import create_tables, drop_tables

logging.basicConfig(level=logging.INFO)


@pytest.fixture(autouse=True, scope="session")
async def test_config():
    config.database_uri = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(autouse=True, scope="function")
async def db_session():
    await create_tables()

    yield

    await drop_tables()


@pytest.fixture
async def session():
    async with config.session() as db:
        yield db


@pytest.fixture
def client() -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(base_url="http://localhost", transport=transport)


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
    ) -> typing.Awaitable[GraphResponse]: ...


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
