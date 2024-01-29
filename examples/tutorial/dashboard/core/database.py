import abc
import datetime
import typing

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped

from dashboard.core.config import config

Model = typing.TypeVar("Model", covariant=True)


class Base(AsyncAttrs, DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "user_account"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str]
    name: Mapped[str]
    password: Mapped[str]
    is_admin: Mapped[bool] = mapped_column(default=False)
    created: Mapped[datetime.datetime] = mapped_column(server_default=func.now())


async def create_tables() -> None:
    async with config.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


class Repository(typing.Generic[Model], abc.ABC):
    """Repository Pattern for our data models."""

    @abc.abstractmethod
    async def get(self, **kwargs) -> typing.Optional[Model]:  # pragma: no cover
        ...

    @abc.abstractmethod
    async def get_all(self, **kwargs) -> typing.List[Model]:  # pragma: no cover
        ...

    @abc.abstractmethod
    async def add(self, **kwargs) -> typing.Optional[Model]:  # pragma: no cover
        ...

    @abc.abstractmethod
    async def delete(self, **kwargs) -> bool:  # pragma: no cover
        ...


class UserRepository(Repository[User]):
    async def get(self, email: str) -> typing.Optional[User]:
        async with config.session() as session:
            result = await session.execute(select(User).where(User.email == email))
            return result.scalars().first()

    async def get_all(self, **kwargs) -> typing.List[User]:
        async with config.session() as session:
            result = await session.execute(select(User))
            return [u for u in result.scalars()]

    async def add(self, name: str, email: str, password: str) -> typing.Optional[User]:
        is_admin = "admin" in email
        async with config.session() as session:
            async with session.begin():
                session.add(
                    User(
                        name=name,
                        email=email,
                        password=password,
                        is_admin=is_admin,
                    )
                )

    async def delete(self, **kwargs) -> bool:
        return False


users = UserRepository()
