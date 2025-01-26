import dataclasses
import logging
import multiprocessing
import socket
import typing

import httpx
import pytest
import uvicorn
from sqlalchemy.ext.asyncio import async_sessionmaker

from dashboard.main import app
from dashboard.core.config import config
from dashboard.core.seed_data import create_tables, drop_tables

logging.basicConfig(level=logging.INFO)
# Add logger for sqlalchemy instead of using `echo=True` to avoid duplicate messages in failures
logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)


def get_free_port():
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def run_server(port):
    uvicorn.run(app, host="0.0.0.0", port=port)


@pytest.fixture(scope="session", autouse=True)
def test_server() -> typing.Generator[str, None, None]:
    port = get_free_port()
    process = multiprocessing.Process(target=run_server, args=(port,))
    process.start()
    yield f"http://localhost:{port}"
    process.terminate()
    process.join()


@pytest.fixture(autouse=True, scope="session")
async def test_config():
    config.database_uri = "sqlite+aiosqlite:///:memory:"
    return config


@pytest.fixture(autouse=True, scope="function")
async def db_session(test_config):
    await create_tables(test_config.engine)

    yield

    await drop_tables(test_config.engine)


@pytest.fixture
async def session():
    async with config.session() as db:
        yield db


@pytest.fixture
async def session_maker() -> async_sessionmaker:
    return config.session


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
