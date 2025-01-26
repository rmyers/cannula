from __future__ import annotations
from sqlalchemy import ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from uuid import UUID


class Base(DeclarativeBase):
    pass


class DBQuota(Base):
    __tablename__ = "quotas_part4"
    id: Mapped[UUID] = mapped_column(primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        foreign_key=ForeignKey("users_part4.id"), nullable=False
    )
    resource: Mapped[str] = mapped_column(nullable=False)
    limit: Mapped[int] = mapped_column(nullable=False)
    count: Mapped[int] = mapped_column(nullable=False)


class DBUser(Base):
    __tablename__ = "users_part4"
    id: Mapped[UUID] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
    email: Mapped[str] = mapped_column(index=True, unique=True, nullable=False)
