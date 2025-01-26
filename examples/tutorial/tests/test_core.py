from dashboard.main import app, lifespan
from dashboard.core.config import Config
from dashboard.core.seed_data import add_data


async def test_add_data(test_config: Config):
    await add_data(test_config.session)


async def test_dashboard(client):
    response = await client.get("/")
    assert "Hello Dashboard Friends" in response.text


async def test_lifespan():
    async with lifespan(app):
        assert 1 == 1
