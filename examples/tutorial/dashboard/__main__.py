import asyncio
import uuid

import click
import uvicorn

from .core.config import config
from .core.database import create_tables
from .core.repository import UserRepository, QuotaRepository


@click.group()
def cli():  # pragma: no cover
    pass


@click.command()
def initdb():  # pragma: no cover
    click.echo("Initialized the database")
    asyncio.run(create_tables())


@click.command()
def run():  # pragma: no cover
    uvicorn.run("dashboard.main:app", reload=True)


async def _add_users():  # pragma: no cover
    async with config.session() as session:
        user_id = uuid.uuid4()
        admin_id = uuid.uuid4()
        users = UserRepository(session=session)
        quotas = QuotaRepository(session=session)
        await users.add(
            id=user_id,
            name="Normal User",
            email="user@email.com",
            password="test1",
        )
        await users.add(
            id=admin_id,
            name="Admin User",
            email="admin@example.com",
            password="test2",
        )
        await quotas.add(user_id=user_id, resource="fire", limit=10, count=4)
        await quotas.add(user_id=user_id, resource="water", limit=15, count=4)
        await quotas.add(user_id=admin_id, resource="fire", limit=5, count=4)


@click.command()
def addusers():  # pragma: no cover
    click.echo("Adding users")
    asyncio.run(_add_users())


cli.add_command(initdb)
cli.add_command(run)
cli.add_command(addusers)

if __name__ == "__main__":  # pragma: no cover
    cli()
