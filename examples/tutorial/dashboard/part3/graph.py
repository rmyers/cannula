import pathlib
from typing import List

import cannula
from sqlalchemy import select

from ..core.config import config
from ..core.database import User
from ._generated import PersonaType, RootType
from .context import Context
from .models import persona


async def resolve_people(
    # Using this type hint for the ResolveInfo will make it so that
    # we can inspect the `info` object in our editors and find the `session`
    info: cannula.ResolveInfo[Context],
) -> List[PersonaType]:
    async with info.context.session() as session:
        query = select(User)
        all_users = await session.scalars(query)
        return [persona(user) for user in all_users]


# The RootType object from _generated will warn us if we use
# a resolver with an incorrect signature
root_value: RootType = {"people": resolve_people}

cannula_app = cannula.CannulaAPI[RootType](
    schema=pathlib.Path(config.root / "part3"),
    root_value=root_value,
)
