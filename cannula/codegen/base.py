import ast
import typing

from cannula.types import Argument, Field

# AST contants for common values
NONE = ast.Constant(value=None)
ELLIPSIS = ast.Expr(value=ast.Constant(value=Ellipsis))
PASS = ast.Pass()


def ast_for_import_from(module: str, names: set[str]) -> ast.ImportFrom:
    ast_names = []
    _names = list(names)
    _names.sort()
    for name in _names:
        ast_name = ast.alias(name=name, asname=None)
        ast_names.append(ast_name)
    return ast.ImportFrom(module=module, names=ast_names, level=0)


def ast_for_name(name: str) -> ast.expr:
    return ast.Name(id=name, ctx=ast.Load())


def ast_for_constant(value: typing.Any) -> ast.expr:
    return ast.Constant(value=value)


def ast_for_docstring(value: str) -> ast.Expr:
    return ast.Expr(value=ast_for_constant(value))


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


def ast_for_argument(arg: Argument) -> ast.arg:
    """
    Create an AST node for a function argument.
    """
    # LOG.debug(f"AST for arg: {arg.__dict__}")
    arg_type = arg.type if arg.required else f"Optional[{arg.type}]"
    return ast.arg(arg=arg.name, annotation=ast.Name(id=arg_type, ctx=ast.Load()))


def ast_for_keyword(arg: str, value: typing.Any) -> ast.keyword:
    return ast.keyword(arg=arg, value=ast_for_constant(value))


def ast_for_subscript(
    value: typing.Union[ast.Name, ast.Attribute, ast.expr], *items: str
) -> ast.Subscript:
    use_tuple = len(items) > 1
    item_names = [ast_for_name(item) for item in items]
    _slice = ast.Tuple(elts=item_names, ctx=ast.Load()) if use_tuple else item_names[0]
    return ast.Subscript(value=value, slice=_slice, ctx=ast.Load())


def ast_for_union_subscript(*items: str) -> ast.Subscript:
    value = ast_for_name("Union")
    return ast_for_subscript(value, *items)


def ast_for_function_body(field: Field) -> list[ast.stmt]:
    body: list[ast.stmt] = []
    if field.description:
        body.append(ast_for_docstring(field.description))

    body.append(ELLIPSIS)
    return body


def ast_for_class_field(field: Field) -> ast.AnnAssign:
    field_type = ast_for_name(field.type)

    # Handle the defaults properly. When the field is required we don't want to
    # set a default value of `None`. But when it is optional we need to properly
    # construct the default using `ast_for_name`.
    default: typing.Optional[ast.expr] = None
    if not field.required:
        default = ast_for_constant(field.default)

    return ast_for_annotation_assignment(
        field.name, annotation=field_type, default=default
    )
