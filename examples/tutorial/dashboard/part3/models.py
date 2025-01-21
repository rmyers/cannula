import uuid
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, async_sessionmaker

from .gql.sql import Base
from .gql.context import (
    UserDatasource,
    QuotaDatasource,
)

engine: AsyncEngine = create_async_engine("sqlite+aiosqlite:///:memory:")
session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def create_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def add_data() -> uuid.UUID:
    users = UserDatasource(session_maker)
    quotas = QuotaDatasource(session_maker)

    user_id = uuid.uuid4()
    await users.add(id=user_id, name="test", email="sam@ex.com")
    await quotas.add(
        id=uuid.uuid4(), user_id=user_id, resource="test", limit=100, count=0
    )
    return user_id
