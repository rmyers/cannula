from __future__ import annotations
from dataclasses import dataclass

from cannula.contrib.orm import DBMixin
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class DBUser(Base):
    __tablename__ = "user"
    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]
    email: Mapped[str]


@dataclass(kw_only=True)
class UserTypeBase:
    id: str
    name: str
    email: str


async def test_db_mixin():
    class User(UserTypeBase, DBMixin[DBUser]):
        pass

    db_model = DBUser(id="1", name="test", email="foo@bar.com")

    user_from_db = User.from_db(db_model)

    assert user_from_db.email == "foo@bar.com"
    assert user_from_db.name == "test"
