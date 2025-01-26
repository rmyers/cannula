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


async def resolve_person(
    info: cannula.ResolveInfo[Context],
    id: uuid.UUID,
) -> Optional[User]:
    return await info.context.users.query_person(id=id)


root_value: RootType = {
    "people": resolve_people,
    "person": resolve_person,
}

cannula_app = cannula.CannulaAPI[RootType](
    schema=pathlib.Path(config.root / "part4"),
    scalars=[UUID],
    root_value=root_value,
)
