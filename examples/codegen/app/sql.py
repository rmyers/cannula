from __future__ import annotations
from sqlalchemy import ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from typing import Optional
from uuid import UUID


class Base(DeclarativeBase):
    pass


class DBQuota(Base):
    __tablename__ = "quota"
    user_id: Mapped[UUID] = mapped_column(
        foreign_key=ForeignKey("users.id"), nullable=False
    )
    user: Mapped[DBUser] = relationship("DBUser", cascade="all")
    resource: Mapped[Optional[str]] = mapped_column(nullable=True)
    limit: Mapped[Optional[int]] = mapped_column(nullable=True)
    count: Mapped[Optional[int]] = mapped_column(nullable=True)


class DBUser(Base):
    """User Model"""

    __tablename__ = "users"
    id: Mapped[UUID] = mapped_column(primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(nullable=True)
    email: Mapped[Optional[str]] = mapped_column(nullable=True)
