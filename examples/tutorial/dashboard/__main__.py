import asyncio

import click
import uvicorn

from dashboard.core.database import create_tables


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


cli.add_command(initdb)
cli.add_command(run)

if __name__ == "__main__":  # pragma: no cover
    cli()
