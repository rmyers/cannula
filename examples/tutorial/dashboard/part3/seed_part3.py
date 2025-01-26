import uuid

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from .gql.context import UserDatasource
from .gql.sql import Base


async def create_tables(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_tables(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def seed_data(session: async_sessionmaker) -> list[uuid.UUID]:
    users = UserDatasource(session)
    user_id = uuid.uuid4()
    await users.add(id=user_id, name="test", email="sam@ex.com")
    another_id = uuid.uuid4()
    await users.add(id=another_id, name="another", email="sammie@ex.com")
    return [user_id, another_id]
