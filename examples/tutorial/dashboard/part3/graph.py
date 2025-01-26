import pathlib
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


# The RootType object generated in `gql/types.py` will warn us if we use
# a resolver with an incorrect signature
root_value: RootType = {
    "people": resolve_people,
}

cannula_app = cannula.CannulaAPI[RootType](
    schema=pathlib.Path(config.root / "part3"),
    scalars=[
        UUID,
    ],
    root_value=root_value,
)
