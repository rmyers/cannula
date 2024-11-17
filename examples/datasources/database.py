import logging
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped

database_uri = "sqlite+aiosqlite:///:memory:"
engine = create_async_engine(database_uri, echo=False)
session = async_sessionmaker(engine, expire_on_commit=False)

aio_logger = logging.getLogger("aiosqlite")
aio_logger.setLevel(logging.ERROR)


class Base(DeclarativeBase): ...


class DBUser(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(unique=True)
    name: Mapped[str]
    password: Mapped[str]


class DBWidget(Base):
    __tablename__ = "widgets"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int]
    name: Mapped[str]
    type: Mapped[str]


async def create_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
