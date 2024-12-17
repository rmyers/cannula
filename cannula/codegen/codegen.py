"""
Code Generation
----------------
"""

import ast
import logging
import pathlib
import typing

from cannula.scalars import ScalarInterface
from graphql import (
    DocumentNode,
)

from cannula.format import format_code
from cannula.codegen.types import Argument, Field, ObjectType, UnionType
from cannula.codegen.parse import parse_schema

LOG = logging.getLogger(__name__)

# AST contants for common values
NONE = ast.Constant(value=None)
ELLIPSIS = ast.Expr(value=ast.Constant(value=Ellipsis))


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


def render_function_args_ast(
    args: list[Argument],
) -> typing.Tuple[list[ast.arg], list[ast.arg], list[ast.expr | None]]:
    """
    Render function arguments as AST nodes.

    This returns a tuple of lists (args, kwargs, defaults). If the field is required
    it is added to args, if it is not required then it is added to kwargs along
    with a default in the defaults list.
    """
    pos_args_ast: list[ast.arg] = [
        ast_for_argument(arg) for arg in args if arg.required
    ]
    kwonly_args_ast: list[ast.arg] = [
        ast_for_argument(arg) for arg in args if not arg.required
    ]
    defaults: list[ast.expr | None] = [
        ast_for_constant(arg.default) for arg in args if not arg.required
    ]
    return pos_args_ast, kwonly_args_ast, defaults


def render_computed_field_ast(field: Field) -> ast.AsyncFunctionDef:
    """
    Render a computed field as an AST node for a function definition.
    """
    pos_args, kwonlyargs, defaults = render_function_args_ast(field.args)
    args = [
        ast.arg("self"),
        ast.arg("info", annotation=ast_for_name("ResolveInfo")),
        *pos_args,
    ]
    args_node = ast.arguments(
        args=args,
        vararg=None,
        posonlyargs=[],
        kwonlyargs=kwonlyargs,
        kw_defaults=defaults,
        kwarg=None,
        defaults=[],
    )
    func_node = ast.AsyncFunctionDef(
        name=field.name,
        args=args_node,
        body=ast_for_function_body(field),
        decorator_list=[ast.Name(id="abstractmethod", ctx=ast.Load())],
        returns=ast.Name(id=field.type, ctx=ast.Load()),
        lineno=None,  # type: ignore
    )
    return func_node


def render_operation_field_ast(field: Field) -> ast.AsyncFunctionDef:
    """
    Render a computed field as an AST node for a function definition.
    """
    pos_args, kwonlyargs, defaults = render_function_args_ast(field.args)
    args = [
        ast.arg("self"),
        ast.arg("info", annotation=ast_for_name("ResolveInfo")),
        *pos_args,
    ]
    # value = field.value if field.required else f"Optional[{field.value}]"
    args_node = ast.arguments(
        args=args,
        vararg=None,
        posonlyargs=[],
        kwonlyargs=kwonlyargs,
        kw_defaults=defaults,
        kwarg=None,
        defaults=[],
    )
    func_node = ast.AsyncFunctionDef(
        name="__call__",
        args=args_node,
        body=ast_for_function_body(field),
        decorator_list=[],
        returns=ast.Name(id=field.type, ctx=ast.Load()),
        lineno=None,  # type: ignore
    )
    return func_node


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


def ast_for_dict_field(field: Field) -> ast.AnnAssign:
    field_type = ast_for_name(field.value)
    return ast_for_annotation_assignment(field.name, annotation=field_type)


def ast_for_operation_field(field: Field) -> ast.AnnAssign:
    field_type = ast_for_name(field.operation_type)
    return ast_for_annotation_assignment(field.name, annotation=field_type)


def render_object(
    obj: ObjectType, use_pydantic: bool = False
) -> list[ast.ClassDef | ast.Assign]:
    non_computed: list[Field] = []
    computed: list[Field] = []
    for field in obj.fields:
        if field.is_computed:
            computed.append(field)
        else:
            non_computed.append(field)

    type_def = ast_for_assign("__typename", ast_for_constant(obj.name))
    klass_fields = [ast_for_class_field(f) for f in non_computed]
    computed_fields = [render_computed_field_ast(f) for f in computed]

    if obj.description:
        doc_string = ast_for_docstring(obj.description)
        constants = [doc_string, type_def]
    else:
        constants = [type_def]

    if use_pydantic:
        return [
            ast.ClassDef(
                name=obj.py_type,
                body=[*constants, *klass_fields, *computed_fields],
                bases=[ast_for_name("BaseModel")],
                keywords=[],
                decorator_list=[],
                # type_params=[],
            ),
        ]

    return [
        ast.ClassDef(
            name=obj.py_type,
            body=[*constants, *klass_fields, *computed_fields],
            bases=[ast_for_name("ABC")],
            keywords=[],
            decorator_list=[
                ast.Call(
                    func=ast_for_name("dataclass"),
                    args=[],
                    keywords=[ast_for_keyword("kw_only", True)],
                )
            ],
            # type_params=[],
        ),
    ]


def render_input(obj: ObjectType) -> list[ast.ClassDef | ast.Assign]:
    type_name = f"{obj.name}Input"

    dict_fields = [ast_for_dict_field(f) for f in obj.fields]
    return [
        ast.ClassDef(
            name=type_name,
            body=[*dict_fields],
            bases=[ast_for_name("TypedDict")],
            keywords=[],
            decorator_list=[],
            # type_params=[],
        )
    ]


def render_interface(obj: ObjectType) -> list[ast.ClassDef | ast.Assign]:
    klass_fields = [ast_for_class_field(f) for f in obj.fields]
    return [
        ast.ClassDef(
            name=obj.py_type,
            body=[*klass_fields],
            bases=[ast_for_name("Protocol")],
            keywords=[],
            decorator_list=[],
            # type_params=[],
        )
    ]


def render_union(obj: UnionType) -> list[ast.ClassDef | ast.Assign]:
    items = [field.value for field in obj.types]
    return [
        ast_for_assign(
            obj.name,
            ast_for_union_subscript(*items),
        )
    ]


def ast_for_operation(field: Field) -> ast.ClassDef:
    func = render_operation_field_ast(field)
    return ast.ClassDef(
        name=field.func_name,
        body=[func],
        bases=[ast_for_name("Protocol")],
        keywords=[],
        decorator_list=[],
        # type_params=[],
    )


def ast_for_root_type(fields: list[Field]) -> ast.ClassDef:
    dict_fields = [ast_for_operation_field(f) for f in fields]
    return ast.ClassDef(
        name="RootType",
        body=[*dict_fields],
        bases=[ast_for_name("TypedDict")],
        keywords=[ast.keyword(arg="total", value=ast_for_constant(False))],
        decorator_list=[],
        # type_params=[],
    )


def render_code(
    type_defs: typing.Iterable[typing.Union[str, DocumentNode]],
    scalars: list[ScalarInterface] = [],
    use_pydantic: bool = False,
) -> str:

    parsed = parse_schema(type_defs, scalars)
    _imports = parsed._schema.extensions.get("imports", {})

    root = ast.Module(body=[], type_ignores=[])

    module_imports = list(_imports.keys())
    module_imports.sort()
    for module in module_imports:
        if module == "builtins":
            continue
        root.body.append(ast_for_import_from(module=module, names=_imports[module]))

    for obj in parsed.interface_types:
        root.body.extend(render_interface(obj))

    for obj in parsed.input_types:
        root.body.extend(render_input(obj))

    for obj in parsed.object_types:
        root.body.extend(render_object(obj, use_pydantic))

    for union_obj in parsed.union_types:
        root.body.extend(render_union(union_obj))

    root.body.extend([ast_for_operation(f) for f in parsed.operation_fields])

    if parsed.operation_fields:
        root.body.append(ast_for_root_type(parsed.operation_fields))

    return format_code(root)


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
