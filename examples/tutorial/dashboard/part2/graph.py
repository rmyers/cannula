import pathlib

import cannula

from ..core.config import config


async def resolve_me(info: cannula.ResolveInfo):
    return {
        # Comment out this next line to reproduce the error in Tutorial
        "__typename": "User",
        "name": "Tiny Tim",
        "email": "tim@example.com",
        "id": "1",
    }


cannula_app = cannula.CannulaAPI(
    schema=pathlib.Path(config.root / "part2"),
    root_value={"me": resolve_me},
)
