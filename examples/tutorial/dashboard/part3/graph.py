import pathlib
import uuid
from typing import Sequence, Optional

import cannula
from cannula.scalars.util import UUID

from ..core.config import config
from .gql.types import User, RootType
from .gql.context import Context


async def resolve_people(
    info: cannula.ResolveInfo[Context],
) -> Optional[Sequence[User]]:
    return await info.context.users.query_people()


async def resolve_user(
    info: cannula.ResolveInfo[Context],
    id: uuid.UUID,
) -> Optional[User]:
    return await info.context.users.query_user(id)


# The RootType object from _generated will warn us if we use
# a resolver with an incorrect signature
root_value: RootType = {
    "people": resolve_people,
    "user": resolve_user,
}

cannula_app = cannula.CannulaAPI[RootType](
    schema=pathlib.Path(config.root / "part3"),
    scalars=[
        UUID,
    ],
    root_value=root_value,
)
