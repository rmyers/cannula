import pytest
from sqlalchemy.exc import IntegrityError

from dashboard.main import app, lifespan
from dashboard.core.database import users, User
from dashboard.core.session import signin, check_session


@pytest.fixture
async def user():
    return await users.add(name="test", email="sam@example.com", password="test")


async def test_dashboard(client):
    response = await client.get("/")
    assert "Hello Dashboard Friends" in response.text


async def test_lifespan():
    async with lifespan(app):
        assert 1 == 1


async def test_users():
    await users.add(name="test", email="sam@example.com", password="test")
    all_users = await users.get_all()
    print(all_users)
    assert len(all_users) == 1

    user = await users.get(email="sam@example.com")
    assert user is not None
    assert user.name == "test"

    deleted = await users.delete()
    assert deleted is False

    with pytest.raises(IntegrityError):
        await users.add(name="test", email="sam@example.com", password="test")


async def test_signin(user: User):
    await users.add(name="signin", email="signin@example.com", password="test2")
    all_users = await users.get_all()
    print(all_users)
    assert len(all_users) == 2

    session = await signin(email="signin@example.com", password="test2")
    assert session is not None


async def test_signin_handles_failures():
    with pytest.raises(Exception, match="Invalid email or password"):
        await signin(email="bad@apple.com", password="anything")


async def test_check_session(user: User):
    not_found = await check_session("anything")
    assert not_found is None

    session = await signin(email=user.email, password=user.password)
    assert session is not None


async def test_auth_login(client, user):
    resp = await client.post(
        "/auth/login",
        data={"email": user.email, "password": user.password},
    )
    assert resp.status_code == 303
    assert resp.headers["location"] == "/"


async def test_auth_logout(client, user):
    resp = await client.get("/auth/logout")
    assert resp.status_code == 303
    assert resp.headers["location"] == "/"
