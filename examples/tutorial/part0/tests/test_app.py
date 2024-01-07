import httpx
import pytest

from dashboard.app import app, lifespan


@pytest.fixture
def client():
    return httpx.AsyncClient(app=app, base_url="http://localhost")


async def test_dashboard(client):
    response = await client.get("/")
    assert "Hello Dashboard Friends" in response.text


async def test_lifespan():
    async with lifespan(app):
        assert 1 == 1
