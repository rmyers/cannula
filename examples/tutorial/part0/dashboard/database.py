from sqlalchemy import MetaData, Table, Column, Integer, String

from dashboard.config import config


metadata = MetaData()


user_table = Table(
    "user_account",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String(100), nullable=False),
    Column("email", String(255), nullable=False),
    Column("password", String(30), nullable=False),
)

project = Table(
    "project",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer, nullable=False),
    Column("name", String(100), nullable=False),
    Column("title", String(255)),
    Column("type", String(30)),
)


async def create_tables() -> None:
    async with config.engine.begin() as conn:
        await conn.run_sync(metadata.create_all)
