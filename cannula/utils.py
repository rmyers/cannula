import ast
import dataclasses
import importlib
import inspect
import logging
import pathlib
import typing

from graphql import parse, DocumentNode
from cannula.scalars import ScalarInterface

LOG = logging.getLogger(__name__)

# AST contants for common values
NONE = ast.Constant(value=None)
ELLIPSIS = ast.Expr(value=ast.Constant(value=Ellipsis))
PASS = ast.Pass()


@dataclasses.dataclass
class CannulaConfig:
    root_path: pathlib.Path
    dest: pathlib.Path
    schema: pathlib.Path
    operations: pathlib.Path
    app_directory: pathlib.Path
    operations_directory: pathlib.Path
    static_directory: pathlib.Path
    use_pydantic: bool = False
    scalars: list[str] = dataclasses.field(default_factory=list)


class ProjectRootError(Exception):
    pass


def find_package_root(
    start_path: typing.Optional[pathlib.Path] = None,
    max_depth: int = 5,
) -> pathlib.Path:
    required_markers: set[str] = {"pyproject.toml"}
    skip_paths = {
        "cannula/utils.py",
        "cannula/api.py",
        "cannula/handlers/application.py",
    }

    if start_path is None:
        caller_frame = inspect.stack()
        for c in caller_frame:
            should_skip = any(p in c.filename for p in skip_paths)
            if should_skip:
                continue
            start_path = pathlib.Path(c.filename).resolve()
            break

    assert start_path is not None
    current = start_path
    depth = 0

    while current != current.parent and depth < max_depth:
        # Check if any required markers exist
        if all((current / marker).exists() for marker in required_markers):
            return current

        current = current.parent
        depth += 1

    raise ProjectRootError(
        f"Could not find project root with markers {required_markers} "
        f"within {max_depth} levels up from {start_path}"
    )


def get_config(start_path: typing.Optional[pathlib.Path] = None) -> CannulaConfig:
    """Searchs the current path for `pyproject.toml` and return options."""
    import tomli

    root = find_package_root(start_path)
    contents = (root / "pyproject.toml").read_text()
    options = tomli.loads(contents)
    config = options.get("tool", {}).get("cannula", {})
    codegen = config.get("codegen", {})
    found = codegen or config
    app_directory = root / found.get("app_directory", "app")
    operations_directory = root / found.get(
        "operations_directory", (app_directory / "_operations")
    )
    static_directory = root / found.get("static_directory", (app_directory / "_static"))
    return CannulaConfig(
        root_path=root,
        dest=(root / found.get("dest", "gql")),
        schema=(root / found.get("schema", "schema.graphql")),
        operations=(root / found.get("operations", "operations.graphql")),
        app_directory=app_directory,
        operations_directory=operations_directory,
        static_directory=static_directory,
        scalars=found.get("scalars", []),
        use_pydantic=found.get("use_pydantic"),
    )


def resolve_scalars(scalars: list[str]) -> list[ScalarInterface]:
    _scalars: list[ScalarInterface] = []
    for scalar in scalars or []:
        _mod, _, _klass = scalar.rpartition(".")
        if not _mod:
            raise AttributeError(
                f"Scalar: {scalar} invalid must be a module path for import like 'my.module.Klass'"
            )
        _parent = importlib.import_module(_mod)
        _klass_obj = getattr(_parent, _klass)
        _scalars.append(_klass_obj)

    return _scalars


def gql(schema: str) -> DocumentNode:
    """
    Helper utility to provide help mark up
    """
    return parse(schema)


def pluralize(name: str) -> str:
    """Pluralized name used for the attribute on the context object.

    Follows English pluralization rules.
    """
    _attr = name.lower()

    # Special cases and irregular plurals could be added here
    irregular_plurals = {
        "person": "people",
        "child": "children",
        "goose": "geese",
        "mouse": "mice",
        "criterion": "criteria",
    }
    if _attr in irregular_plurals:
        return irregular_plurals[_attr]

    # Words ending in -is change to -es
    if _attr.endswith("is"):
        return f"{_attr[:-2]}es"

    # Words ending in -us change to -i
    if _attr.endswith("us"):
        return f"{_attr[:-2]}i"

    # Words ending in -on change to -a
    if _attr.endswith("on"):
        return f"{_attr[:-2]}a"

    # Words ending in sibilant sounds (s, sh, ch, x) add -es
    if _attr.endswith(("s", "sh", "ch", "x", "zz")):
        return f"{_attr}es"

    # Words ending in -z double the z and add -es
    if _attr.endswith("z"):
        return f"{_attr}zes"

    # Words ending in consonant + y change y to ies
    if _attr.endswith("y") and len(_attr) > 1 and _attr[-2] not in "aeiou":
        return f"{_attr[:-1]}ies"

    # Words ending in -f or -fe change to -ves
    if _attr.endswith("fe"):
        return f"{_attr[:-2]}ves"
    if _attr.endswith("f"):
        return f"{_attr[:-1]}ves"

    # Words ending in -o: some add -es, most just add -s
    o_es_endings = {
        "hero",
        "potato",
        "tomato",
        "echo",
        "veto",
        "volcano",
        "tornado",
    }
    if _attr in o_es_endings:
        return f"{_attr}es"

    # Default case: just add s
    return f"{_attr}s"


def ast_for_import_from(module: str, names: set[str], level: int = 0) -> ast.ImportFrom:
    ast_names = []
    _names = list(names)
    _names.sort()
    for name in _names:
        ast_name = ast.alias(name=name, asname=None)
        ast_names.append(ast_name)
    return ast.ImportFrom(module=module, names=ast_names, level=level)


def ast_for_name(name: str) -> ast.expr:
    return ast.Name(id=name, ctx=ast.Load())


def ast_for_constant(value: typing.Any) -> ast.expr:
    return ast.Constant(value=value)


def ast_for_docstring(value: str) -> ast.Expr:
    newline = "\n" if "\n" in value else ""
    newline = "" if value.startswith("\n") else newline
    docstring = f"{newline}{value}{newline}"
    return ast.Expr(value=ast_for_constant(docstring))


def ast_for_annotation_assignment(
    target: str, annotation: ast.expr, default: typing.Optional[typing.Any] = None
) -> ast.AnnAssign:
    return ast.AnnAssign(
        target=ast.Name(id=target, ctx=ast.Store()),
        annotation=annotation,
        value=default,
        simple=1,
    )


def ast_for_assign(target: str, value: ast.expr) -> ast.Assign:
    targets = [ast_for_name(target)]
    return ast.Assign(
        targets=targets,
        value=value,
        lineno=None,  # type: ignore
    )


def ast_for_keyword(arg: str, value: typing.Any) -> ast.keyword:
    return ast.keyword(arg=arg, value=ast_for_constant(value))


def ast_for_subscript(
    value: typing.Union[ast.Name, ast.Attribute, ast.expr], *items: str
) -> ast.Subscript:
    use_tuple = len(items) > 1
    item_names = [ast_for_name(item) for item in items]
    _slice = ast.Tuple(elts=item_names, ctx=ast.Load()) if use_tuple else item_names[0]
    return ast.Subscript(value=value, slice=_slice, ctx=ast.Load())


def ast_for_single_subscript(
    value: typing.Union[ast.Name, ast.Attribute, ast.expr], item: ast.expr
) -> ast.Subscript:
    return ast.Subscript(value=value, slice=item, ctx=ast.Load())


def ast_for_union_subscript(*items: str) -> ast.Subscript:
    value = ast_for_name("Union")
    return ast_for_subscript(value, *items)
