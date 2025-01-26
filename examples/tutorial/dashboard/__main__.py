import asyncio

import click
import uvicorn

from .core.config import config
from .core.seed_data import create_tables, add_data


@click.group()
def cli():  # pragma: no cover
    pass


@click.command()
def initdb():  # pragma: no cover
    click.echo("Initialized the database")
    asyncio.run(create_tables(config.engine))


@click.command()
def run():  # pragma: no cover
    uvicorn.run("dashboard.main:app", port=config.port, host=config.host, reload=True)


@click.command()
def addusers():  # pragma: no cover
    click.echo("Adding users")
    asyncio.run(add_data(config.session))


cli.add_command(initdb)
cli.add_command(run)
cli.add_command(addusers)

if __name__ == "__main__":  # pragma: no cover
    cli()
