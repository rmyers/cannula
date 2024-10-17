import asyncio

import click
import uvicorn

from .core.config import config
from .core.database import create_tables
from .core.repository import UserRepository


@click.group()
def cli():  # pragma: no cover
    pass


@click.command()
def initdb():  # pragma: no cover
    click.echo("Initialized the database")
    loop = asyncio.get_event_loop()
    loop.run_until_complete(create_tables())


@click.command()
def run():  # pragma: no cover
    uvicorn.run("dashboard.main:app", reload=True)


async def _add_users():  # pragma: no cover
    async with config.session() as session:
        users = UserRepository(session)
        await users.add("Normal User", email="user@email.com", password="test1")
        await users.add("Admin User", email="admin@example.com", password="test2")


@click.command()
def addusers():  # pragma: no cover
    click.echo("Adding users")
    loop = asyncio.get_event_loop()
    loop.run_until_complete(_add_users())


cli.add_command(initdb)
cli.add_command(run)
cli.add_command(addusers)

if __name__ == "__main__":  # pragma: no cover
    cli()
