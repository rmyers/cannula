import pathlib
import functools

from fastapi.templating import Jinja2Templates
from pydantic_settings import BaseSettings
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

DASHBOARD_ROOT = pathlib.Path(__file__).parent.parent


class Config(BaseSettings):
    database_uri: str = "sqlite+aiosqlite:///db.sqlite"
    debug: bool = True
    template_dir: str = "templates"

    @functools.cached_property
    def root(self):
        return DASHBOARD_ROOT

    @functools.cached_property
    def templates(self):
        return Jinja2Templates(self.root / self.template_dir)

    @functools.cached_property
    def engine(self):
        return create_async_engine(self.database_uri)

    @property
    def session(self):
        return async_sessionmaker(self.engine, expire_on_commit=False)


config = Config()
