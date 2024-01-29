import pytest

from dashboard.main import app, lifespan
from dashboard.core.database import create_tables, users
from dashboard.core.session import signin


async def test_dashboard(client):
    response = await client.get("/")
    assert "Hello Dashboard Friends" in response.text


async def test_lifespan():
    async with lifespan(app):
        assert 1 == 1


async def test_create_tables():
    await create_tables()

    await users.add(name="test", email="sam@example.com", password="test")
    all_users = await users.get_all()
    print(all_users)
    assert len(all_users) == 1

    user = await users.get(email="sam@example.com")
    assert user is not None
    assert user.name == "test"

    deleted = await users.delete()
    assert deleted is False


async def test_signin():
    await create_tables()

    await users.add(name="signin", email="signin@example.com", password="test2")
    all_users = await users.get_all()
    print(all_users)
    assert len(all_users) == 2

    session = await signin(email="signin@example.com", password="test2")
    assert session is not None


async def test_signin_handles_failures():
    with pytest.raises(Exception, match="Invalid email or password"):
        await signin(email="bad@apple.com", password="anything")
