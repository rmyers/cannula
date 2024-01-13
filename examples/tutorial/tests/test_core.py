import httpx
import pytest

from dashboard.core.app import app, lifespan
from dashboard.core.config import config
from dashboard.core.database import create_tables, user_table


@pytest.fixture
def client():
    return httpx.AsyncClient(app=app, base_url="http://localhost")


async def test_dashboard(client):
    response = await client.get("/")
    assert "Hello Dashboard Friends" in response.text


async def test_lifespan():
    async with lifespan(app):
        assert 1 == 1


async def test_create_tables():
    await create_tables()
    async with config.engine.begin() as conn:
        result = await conn.execute(user_table.select())
        rows = result.fetchall()
        assert len(rows) == 0
