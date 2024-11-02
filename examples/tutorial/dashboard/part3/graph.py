import pathlib
from typing import List

import cannula

from ..core.config import config
from ._generated import PersonaType, RootType
from .context import Context
from .models import persona


async def resolve_people(
    # Using this type hint for the ResolveInfo will make it so that
    # we can inspect the `info` object in our editors and find the `user_repo`
    info: cannula.ResolveInfo[Context],
) -> List[PersonaType]:
    all_users = await info.context.user_repo.filter()
    return [persona(user) for user in all_users]


# The RootType object from _generated will warn us if we use
# a resolver with an incorrect signature
root_value: RootType = {"people": resolve_people}

cannula_app = cannula.API[RootType](
    schema=pathlib.Path(config.root / "part3"),
    root_value=root_value,
)
