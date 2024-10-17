import datetime
import pytest
from sqlalchemy.exc import IntegrityError

from dashboard.main import app, lifespan
from dashboard.core.database import User
from dashboard.core.repository import UserRepository
from dashboard.core.session import check_session


@pytest.fixture
async def user(session):
    users = UserRepository(session=session)
    return await users.add(name="test", email="sam@example.com", password="test")


async def test_dashboard(client):
    response = await client.get("/")
    assert "Hello Dashboard Friends" in response.text


async def test_lifespan():
    async with lifespan(app):
        assert 1 == 1


async def test_users(session):
    users = UserRepository(session=session)
    user = await users.add(name="test", email="sam@example.com", password="test")
    all_users = await users.filter()
    print(all_users)
    assert len(all_users) == 1

    user = await users.get(pk=user.id)
    assert user is not None
    assert user.name == "test"
    assert isinstance(user.created, datetime.datetime)

    with pytest.raises(IntegrityError):
        await users.add(name="test", email="sam@example.com", password="test")


async def test_signin(user: User, session):
    users = UserRepository(session=session)
    await users.add(name="signin", email="signin@example.com", password="test2")
    all_users = await users.filter()
    print(all_users)
    assert len(all_users) == 2

    session = await users.signin(email="signin@example.com", password="test2")
    assert session is not None


async def test_signin_handles_failures(session):
    users = UserRepository(session=session)
    with pytest.raises(Exception, match="Invalid email or password"):
        await users.signin(email="bad@apple.com", password="anything")


async def test_check_session(user: User, session):
    users = UserRepository(session=session)
    not_found = await check_session("anything")
    assert not_found is None

    session = await users.signin(email=user.email, password=user.password)
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
