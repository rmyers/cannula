import dataclasses
import pytest
from sqlalchemy.ext.asyncio import AsyncAttrs, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped

from cannula.datasource.orm import DatabaseRepository

database_uri = "sqlite+aiosqlite:///:memory:"
engine = create_async_engine(database_uri, echo=True)
session = async_sessionmaker(engine, expire_on_commit=False)


class Base(AsyncAttrs, DeclarativeBase):
    pass


class DBUser(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(unique=True)
    name: Mapped[str]
    password: Mapped[str]


@dataclasses.dataclass
class User:
    id: int
    email: str | None
    name: str | None
    password: str | None


async def create_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


class UserRepository(
    DatabaseRepository[DBUser, User],
    db_model=DBUser,
    graph_model=User,
):
    pass


@pytest.fixture(autouse=True)
async def db_session():
    await create_tables()
    yield
    await drop_tables()


async def test_orm_defaults(mocker):
    mock_logger = mocker.patch("cannula.datasource.orm.LOG")
    users = UserRepository(session)
    new_user = await users.add(id=1, name="test", email="u@c.com", password="secret")
    assert new_user.id == 1

    all_users = await users.get_models()
    assert len(all_users) == 1
    assert all_users[0].name == "test"

    specific_user = await users.get_model(1)
    assert specific_user is not None
    assert specific_user.name == "test"

    specific_user_again = await users.get_model(1)
    assert specific_user_again is not None
    mock_logger.debug.assert_called_with("Found cached query for get:1")
    mock_logger.reset()

    not_found = await users.get_model(2)
    assert not_found is None

    query_user = await users.get_model_by_query(DBUser.email == "u@c.com")
    assert query_user is not None
    assert query_user.password == "secret"

    query_user_again = await users.get_model_by_query(DBUser.email == "u@c.com")
    assert query_user_again is not None
    mock_logger.debug.assert_called_with("Found cached query for UserRepository")
    mock_logger.reset()

    query_not_found = await users.get_model_by_query(DBUser.email == "not-found")
    assert query_not_found is None

    filter_users = await users.get_models(DBUser.name == "test")
    assert len(filter_users) == 1

    filter_users_again = await users.get_models(DBUser.name == "test")
    assert len(filter_users_again) == 1
    mock_logger.debug.assert_called_with("Found cached results for UserRepository")
    mock_logger.reset()


async def test_invalid_graph_model():
    class NotCorrect:
        pass

    with pytest.raises(
        ValueError,
        match="Invalid model for 'GraphModel' must be a dataclass or pydantic model",
    ):

        class InvalidRepository(
            DatabaseRepository[DBUser, NotCorrect],
            db_model=DBUser,
            graph_model=NotCorrect,
        ):
            pass
