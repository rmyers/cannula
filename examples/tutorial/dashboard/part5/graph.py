import pathlib
import uuid
from typing import Sequence, Optional

import cannula
from cannula.scalars.util import UUID

from ..core.config import config
from .gql.types import User, RootType
from .gql.context import Context


async def resolve_people(
    # Using this type hint for the ResolveInfo will make it so that
    # we can inspect the `info` object in our editors and find the `user_repo`
    info: cannula.ResolveInfo[Context],
) -> Optional[Sequence[User]]:
    return await info.context.users.query_people()


async def resolve_person(
    # Using this type hint for the ResolveInfo will make it so that
    # we can inspect the `info` object in our editors and find the `user_repo`
    info: cannula.ResolveInfo[Context],
    id: uuid.UUID,
) -> User | None:
    return await info.context.users.query_person(id=id)


# The RootType object from _generated will warn us if we use
# a resolver with an incorrect signature
root_value: RootType = {
    "people": resolve_people,
    "person": resolve_person,
}

cannula_app = cannula.CannulaAPI[RootType](
    schema=pathlib.Path(config.root / "part5"),
    root_value=root_value,
    scalars=[UUID],
)
