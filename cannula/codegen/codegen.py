"""
Code Generation
----------------
"""

import collections
import logging
import pathlib
import typing

from cannula.codegen.generate_types import PythonCodeGenerator
from cannula.codegen.generate_sql import SQLAlchemyGenerator
from cannula.codegen.schema_analyzer import SchemaAnalyzer
from cannula.scalars import ScalarInterface
from cannula.schema import Imports, build_and_extend_schema
from graphql import DocumentNode

LOG = logging.getLogger(__name__)

_IMPORTS: Imports = collections.defaultdict(set[str])
_IMPORTS.update(
    {
        "__future__": {"annotations"},
        "abc": {"ABC", "abstractmethod"},
        "cannula": {"ResolveInfo"},
        "dataclasses": {"dataclass"},
        "pydantic": {"BaseModel"},
        "typing": {
            "Any",
            "Awaitable",
            "Sequence",
            "Optional",
            "Protocol",
            "TYPE_CHECKING",
            "Union",
        },
        "typing_extensions": {"TypedDict", "NotRequired"},
        "sqlalchemy": {"ForeignKey", "select", "func"},
        "sqlalchemy.ext.asyncio": {"AsyncAttrs"},
        "sqlalchemy.orm": {
            "DeclarativeBase",
            "mapped_column",
            "Mapped",
            "relationship",
        },
    }
)


class Generated(typing.TypedDict):
    types: str
    sql: str


def render_code(
    type_defs: typing.Iterable[typing.Union[str, DocumentNode]],
    scalars: list[ScalarInterface] = [],
    use_pydantic: bool = False,
) -> Generated:
    schema = build_and_extend_schema(type_defs, scalars, {"imports": _IMPORTS})
    analyzer = SchemaAnalyzer(schema)

    return {
        "types": PythonCodeGenerator(analyzer).generate(use_pydantic),
        "sql": SQLAlchemyGenerator(analyzer).generate(),
    }


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

    dest.mkdir(parents=True, exist_ok=True)

    if formatted_code["types"]:
        with open(dest / "types.py", "w") as types_file:
            types_file.write(formatted_code["types"])
    if formatted_code["sql"]:
        with open(dest / "sql.py", "w") as sql_file:
            sql_file.write(formatted_code["sql"])
