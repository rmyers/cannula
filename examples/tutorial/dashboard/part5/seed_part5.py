import uuid

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from .gql.context import UserDatasource, QuotaDatasource
from .gql.sql import Base


async def create_tables(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_tables(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def seed_data(session: async_sessionmaker) -> None:
    user_id = uuid.uuid4()
    admin_id = uuid.uuid4()
    users = UserDatasource(session)
    quotas = QuotaDatasource(session)
    await users.add(id=user_id, name="test", email="sam@example.com")
    await users.add(id=admin_id, name="adder", email="admin@example.com")
    await quotas.add(
        id=uuid.uuid4(), user_id=user_id, resource="fire", limit=10, count=4
    )
    await quotas.add(
        id=uuid.uuid4(), user_id=user_id, resource="water", limit=15, count=4
    )
    await quotas.add(
        id=uuid.uuid4(), user_id=admin_id, resource="fire", limit=5, count=4
    )
