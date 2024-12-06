import pathlib
import functools

from cannula.contrib.config import BaseConfig
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, async_sessionmaker

DASHBOARD_ROOT = pathlib.Path(__file__).parent.parent


class Config(BaseConfig):
    database_uri: str = "sqlite+aiosqlite:///db.sqlite"
    debug: bool = True
    template_dir: str = "templates"
    static_dir: str = "static"
    port: int = 8000
    host: str = "0.0.0.0"

    @functools.cached_property
    def root(self) -> pathlib.Path:
        return DASHBOARD_ROOT

    @functools.cached_property
    def templates(self) -> Jinja2Templates:
        return Jinja2Templates(self.root / self.template_dir)

    @functools.cached_property
    def static_files(self) -> pathlib.Path:
        return self.root / self.static_dir

    @functools.cached_property
    def engine(self) -> AsyncEngine:
        return create_async_engine(self.database_uri, echo=True)

    @property
    def session(self) -> async_sessionmaker:
        return async_sessionmaker(self.engine, expire_on_commit=False)


config = Config()
