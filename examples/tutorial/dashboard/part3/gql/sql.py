from __future__ import annotations
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from typing import Optional
from uuid import UUID


class Base(DeclarativeBase):
    pass


class DBUser(Base):
    __tablename__ = "users_part3"
    id: Mapped[UUID] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
    email: Mapped[Optional[str]] = mapped_column(index=True, unique=True, nullable=True)
