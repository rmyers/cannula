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
from cannula.codegen.base import (
    ast_for_annotation_assignment,
    ast_for_assign,
    ast_for_argument,
    ast_for_class_field,
    ast_for_constant,
    ast_for_docstring,
    ast_for_keyword,
    ast_for_import_from,
    ast_for_name,
    ast_for_union_subscript,
    ast_for_function_body,
)

from cannula.codegen.generate_sql import generate_sqlalchemy_models
from cannula.codegen.types import Argument, Field, ObjectType, UnionType
from cannula.codegen.parse import parse_schema

LOG = logging.getLogger(__name__)


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


def render_code_new(
    type_defs: typing.Iterable[typing.Union[str, DocumentNode]],
    scalars: list[ScalarInterface] = [],
) -> str:

    parsed = parse_schema(type_defs, scalars)

    module = generate_sqlalchemy_models(parsed._schema)
    return format_code(module)


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
