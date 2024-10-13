import abc
import datetime
import uuid
import typing

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped

from .config import config

Model = typing.TypeVar("Model", covariant=True)


class Base(AsyncAttrs, DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "user_account"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(unique=True)
    name: Mapped[str]
    password: Mapped[str]
    is_admin: Mapped[bool] = mapped_column(default=False)
    created: Mapped[datetime.datetime] = mapped_column(server_default=func.now())


async def create_tables() -> None:
    async with config.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_tables() -> None:
    async with config.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


class Repository(typing.Generic[Model], abc.ABC):
    """Repository Pattern for our data models."""

    @abc.abstractmethod
    async def get(self, **kwargs) -> typing.Optional[Model]:  # pragma: no cover
        ...

    @abc.abstractmethod
    async def get_all(self, **kwargs) -> typing.List[Model]:  # pragma: no cover
        ...

    @abc.abstractmethod
    async def add(self, **kwargs) -> Model:  # pragma: no cover
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

    async def add(
        self,
        name: str,
        email: str,
        password: str,
        id: typing.Optional[uuid.UUID] = None,
    ) -> User:
        is_admin = "admin" in email
        user_id = id or uuid.uuid4()
        new_user = User(
            id=user_id,
            name=name,
            email=email,
            password=password,
            is_admin=is_admin,
        )
        async with config.session() as session:
            async with session.begin():
                session.add(new_user)
        return new_user

    async def delete(self, **kwargs) -> bool:
        return False


users = UserRepository()
