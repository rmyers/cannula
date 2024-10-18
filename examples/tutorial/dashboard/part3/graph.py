from __future__ import annotations

import pathlib
from typing import List, Optional

import cannula

from ..core.config import config
from ..core.database import User as DBUser
from ..core.repository import UserRepository, DBMixin
from ._generated import PersonaType, RootType, UserType, AdminType


class User(UserType, DBMixin[DBUser, UserType]):
    """User instance"""


class Admin(AdminType, DBMixin[DBUser, AdminType]):
    """Admin instance"""


# need to rebuild these since the Annotations are not fully registered
User.model_rebuild()
Admin.model_rebuild()


def persona(db_user: DBUser) -> PersonaType:
    if db_user.is_admin:
        return Admin.from_db(db_user)
    return User.from_db(db_user)


async def resolve_people(info: cannula.ResolveInfo) -> List[PersonaType]:
    async with config.session() as session:
        users = UserRepository(session)
        all_users = await users.filter()
        return [persona(user) for user in all_users]


root_value: RootType = {"people": resolve_people}

cannula_app = cannula.API[RootType](
    schema=pathlib.Path(config.root / "part3"),
    root_value=root_value,
)
