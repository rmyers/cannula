from dashboard.database import create_tables, user_table
from dashboard.config import config


async def test_create_tables():
    await create_tables()
    async with config.engine.begin() as conn:
        result = await conn.execute(user_table.select())
        rows = result.fetchall()
        assert len(rows) == 0
