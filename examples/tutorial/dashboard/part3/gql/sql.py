from __future__ import annotations
from sqlalchemy import ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from typing import Optional
from uuid import UUID


class Base(DeclarativeBase):
    pass


class DBQuota(Base):
    __tablename__ = "quotas"
    id: Mapped[UUID] = mapped_column(primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    resource: Mapped[Optional[str]] = mapped_column(nullable=True)
    limit: Mapped[Optional[int]] = mapped_column(nullable=True)
    count: Mapped[Optional[int]] = mapped_column(nullable=True)


class DBUser(Base):
    __tablename__ = "users"
    id: Mapped[UUID] = mapped_column(primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(nullable=True)
    email: Mapped[Optional[str]] = mapped_column(nullable=True)
