"""
Code Generation
----------------
"""

import logging
import pathlib
import typing

from cannula.codegen.generate_types import render_code
from cannula.scalars import ScalarInterface
from graphql import DocumentNode

LOG = logging.getLogger(__name__)


def render_file(
    type_defs: typing.Iterable[typing.Union[str, DocumentNode]],
    dest: pathlib.Path,
    scalars: list[ScalarInterface] = [],
    use_pydantic: bool = False,
    dry_run: bool = False,
) -> None:
    formatted_code = render_code(
        type_defs=type_defs, scalars=scalars, use_pydantic=use_pydantic
    )

    if dry_run:
        LOG.info(f"DRY_RUN would produce: \n{formatted_code}")
        return

    with open(dest, "w") as final_file:
        final_file.write(formatted_code)
