from __future__ import annotations
import datetime
import uuid
import typing

from sqlalchemy import ForeignKey, func
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped, relationship

from .config import config


class Base(AsyncAttrs, DeclarativeBase):
    """Base database model."""

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    created: Mapped[datetime.datetime] = mapped_column(server_default=func.now())


class User(Base):
    __tablename__ = "user_account"

    email: Mapped[str] = mapped_column(unique=True)
    name: Mapped[str]
    password: Mapped[typing.Optional[str]]
    is_admin: Mapped[bool] = mapped_column(default=False)
    quota: Mapped[typing.List[Quota]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Quota(Base):
    __tablename__ = "user_quota"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user_account.id"))
    resource: Mapped[str]
    limit: Mapped[int]
    count: Mapped[int]

    user: Mapped[User] = relationship(back_populates="quota")


async def create_tables() -> None:
    async with config.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_tables() -> None:
    async with config.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
