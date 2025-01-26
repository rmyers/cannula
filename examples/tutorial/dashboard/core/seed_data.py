from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from ..part3 import seed_part3
from ..part4 import seed_part4
from ..part5 import seed_part5


async def create_tables(engine: AsyncEngine) -> None:
    await seed_part3.create_tables(engine)
    await seed_part4.create_tables(engine)
    await seed_part5.create_tables(engine)


async def drop_tables(engine: AsyncEngine) -> None:
    await seed_part3.drop_tables(engine)
    await seed_part4.drop_tables(engine)
    await seed_part5.drop_tables(engine)


async def add_data(session: async_sessionmaker) -> None:
    await seed_part3.seed_data(session)
    await seed_part4.seed_data(session)
    await seed_part5.seed_data(session)
