from __future__ import annotations
from datetime import datetime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from typing import Optional


class Base(DeclarativeBase):
    pass


class DBBook(Base):
    """books are cool"""

    __tablename__ = "books"
    name: Mapped[str] = mapped_column(nullable=False)
    author: Mapped[Optional[str]] = mapped_column(nullable=True)


class DBMovie(Base):
    """
    Movie Type

    Includes a book reference defined in other schema file.
    """

    __tablename__ = "movies"
    name: Mapped[str] = mapped_column(nullable=False)
    director: Mapped[Optional[str]] = mapped_column(nullable=True)
    views: Mapped[Optional[int]] = mapped_column(nullable=True)
    created: Mapped[Optional[datetime]] = mapped_column(nullable=True)
