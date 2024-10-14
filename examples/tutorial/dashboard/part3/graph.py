import pathlib

import cannula

from ..core.config import config
from ..core.database import User as DBUser
from ._generated import RootType, PersonaType, UserTypeBase


class User(UserTypeBase):
    _baseObject: DBUser


async def resolve_me(info: cannula.ResolveInfo) -> PersonaType:
    return User(id="1", name="Tiny Tim", email="foo@bar.com")


cannula_app = cannula.API[RootType](
    schema=pathlib.Path(config.root / "part3"),
    root_value={"me": resolve_me},
)
