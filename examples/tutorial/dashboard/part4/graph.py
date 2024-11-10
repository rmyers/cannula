import pathlib
from typing import List

import cannula

from sqlalchemy import select

from ..core.config import config
from ..core.database import User as DBUser
from ._generated import UserType, RootType
from .context import Context
from .models import User


async def resolve_people(
    # Using this type hint for the ResolveInfo will make it so that
    # we can inspect the `info` object in our editors and find the `user_repo`
    info: cannula.ResolveInfo[Context],
) -> List[UserType]:
    async with info.context.session() as session:
        query = select(DBUser)
        all_users = await session.scalars(query)
        return [User.from_db(user) for user in all_users]


# The RootType object from _generated will warn us if we use
# a resolver with an incorrect signature
root_value: RootType = {"people": resolve_people}

cannula_app = cannula.CannulaAPI[RootType](
    schema=pathlib.Path(config.root / "part4"),
    root_value=root_value,
)
