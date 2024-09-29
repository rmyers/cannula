"""
Code Generation
----------------
"""

import ast
import keyword
import logging
import pathlib
import pprint
import typing

from graphql import (
    DocumentNode,
    Node,
)

from cannula.format import format_with_ruff
from cannula.schema import concat_documents
from cannula.types import Argument, Directive, Field, FieldType, ObjectType

LOG = logging.getLogger(__name__)

TYPES = {
    "Boolean": "bool",
    "Float": "float",
    "ID": "str",
    "Int": "int",
    "String": "str",
}
VALUE_FUNCS = {
    "boolean_value": lambda value: value in ["true", "True"],
    "int_value": lambda value: int(value),
    "float_value": lambda value: float(value),
}

# AST contants for common values
NONE = ast.Constant(value=None)
ELLIPSIS = ast.Expr(value=ast.Constant(value=Ellipsis))


def ast_for_import(module: str) -> ast.Import:
    return ast.Import(names=[ast.alias(name=module, asname=None)])


def ast_for_import_from(module: str, names: typing.List[str]) -> ast.ImportFrom:
    ast_names = []
    for name in names:
        name = ast.alias(name=name, asname=None)
        ast_names.append(name)
    return ast.ImportFrom(module=module, names=ast_names, level=0)


def ast_for_name(name: str) -> ast.Name:
    return ast.Name(id=name, ctx=ast.Load())


def ast_for_attribute(target: str, attr: str) -> ast.Attribute:
    return ast.Attribute(
        value=ast.Name(id=target, ctx=ast.Load()), attr=attr, ctx=ast.Load()
    )


RESOLVE_INFO = ast_for_attribute("cannula", "ResolveInfo")


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
        lineno=None,
    )


def ast_for_class(name: str, bases: typing.List[str]) -> ast.ClassDef:
    return ast.ClassDef(
        name=name,
        bases=bases,
        keywords=[],
        body=[],
        decorator_list=[],
    )


def ast_for_argument(arg: Argument) -> ast.arg:
    """
    Create an AST node for a function argument.
    """
    return ast.arg(arg=arg.name, annotation=ast.Name(id=arg.type, ctx=ast.Load()))


def ast_for_subscript(
    value: typing.Union[ast.Name, ast.Attribute], *items: str
) -> ast.Subscript:
    use_tuple = len(items) > 1
    item_names = [ast_for_name(item) for item in items]
    _slice = ast.Tuple(elts=item_names, ctx=ast.Load()) if use_tuple else item_names[0]
    return ast.Subscript(value=value, slice=_slice, ctx=ast.Load())


def ast_for_union_subscript(*items: str) -> ast.Subscript:
    value = ast_for_name("Union")
    return ast_for_subscript(value, *items)


def render_function_args_ast(args: typing.List[Argument]) -> typing.List[ast.arg]:
    """
    Render function arguments as AST nodes.
    """
    return [ast_for_argument(arg) for arg in args]


def render_computed_field_ast(field: Field) -> ast.FunctionDef:
    """
    Render a computed field as an AST node for a function definition.
    """
    args = render_function_args_ast(field.args)
    value = field.value if field.required else f"Optional[{field.value}]"
    args_node = ast.arguments(
        args=args,
        vararg=None,
        posonlyargs=[],
        kwonlyargs=[],
        kw_defaults=[],
        kwarg=None,
        defaults=[],
    )
    func_node = ast.FunctionDef(
        name=field.name,
        args=args_node,
        body=[ast.Pass()],  # Placeholder for the function body
        decorator_list=[ast.Name(id="abc.abstractmethod", ctx=ast.Load())],
        returns=ast.Name(id=f"Awaitable[{value}]", ctx=ast.Load()),
        lineno=None,
    )
    return func_node


def render_operation_field_ast(field: Field) -> ast.FunctionDef:
    """
    Render a computed field as an AST node for a function definition.
    """
    pos_args = render_function_args_ast(field.args)
    args = [
        ast.arg("self"),
        ast.arg("info", annotation=ast_for_name("cannula.ResolveInfo")),
        *pos_args,
    ]
    # value = field.value if field.required else f"Optional[{field.value}]"
    args_node = ast.arguments(
        args=args,
        vararg=None,
        posonlyargs=[],
        kwonlyargs=[],
        kw_defaults=[],
        kwarg=None,
        defaults=[],
    )
    func_node = ast.FunctionDef(
        name="__call__",
        args=args_node,
        body=[ELLIPSIS],  # Placeholder for the function body
        decorator_list=[],
        returns=ast.Name(id=f"Awaitable[{field.value}]", ctx=ast.Load()),
        lineno=None,
    )
    return func_node


def parse_description(obj: dict) -> typing.Optional[str]:
    raw_description = obj.get("description") or {}
    return raw_description.get("value")


def parse_name(obj: dict) -> str:
    raw_name = obj.get("name") or {}
    return raw_name.get("value", "unknown")


def parse_value(obj: dict) -> typing.Any:
    kind = obj["kind"]
    value = obj["value"]

    if func := VALUE_FUNCS.get(kind):
        return func(value)

    return value


def parse_args(obj: dict) -> typing.List[Argument]:
    args: typing.List[Argument] = []
    raw_args = obj.get("arguments") or []
    for arg in raw_args:
        name = parse_name(arg)
        arg_type = FieldType(value=None, required=False)
        raw_type = arg.get("type")
        if raw_type:
            arg_type = parse_type(raw_type)
        value = None
        raw_value = arg.get("value")
        if raw_value:
            value = parse_value(raw_value)
        default = parse_default(arg)
        args.append(
            Argument(
                name=name,
                type=arg_type.value,
                required=arg_type.required,
                value=value,
                default=default,
            )
        )

    return args


def parse_type(type_obj: dict) -> FieldType:
    required = False
    value = None

    if type_obj["kind"] == "non_null_type":
        required = True
        value = parse_type(type_obj["type"]).value

    if type_obj["kind"] == "list_type":
        list_type = parse_type(type_obj["type"]).value
        value = f"List[{list_type}]"

    if type_obj["kind"] == "named_type":
        name = type_obj["name"]
        value = name["value"]
        if value in TYPES:
            value = TYPES[value]
        else:
            value = f"{value}Type"

    return FieldType(value=value, required=required)


def parse_directives(field: typing.Dict[str, typing.Any]) -> typing.List[Directive]:
    directives: typing.List[Directive] = []
    for directive in field.get("directives", []):
        name = parse_name(directive)
        args = parse_args(directive)
        directives.append(Directive(name=name, args=args))
    return directives


def parse_default(obj: typing.Dict[str, typing.Any]) -> typing.Any:
    default_value = obj.get("default_value")
    LOG.debug(default_value)
    if not default_value:
        return None

    return parse_value(default_value)


def parse_field(field: typing.Dict[str, typing.Any], parent: str) -> Field:
    name = field["name"]["value"]
    field_type = parse_type(field["type"])
    default = parse_default(field)
    directives = parse_directives(field)
    args = parse_args(field)
    func_name = f"{name}{parent}"

    return Field(
        name=name,
        value=field_type.value,
        func_name=func_name,
        description=parse_description(field),
        directives=directives,
        args=args,
        default=default,
        required=field_type.required,
    )


def parse_node(node: Node):
    details = node.to_dict()
    LOG.debug("%s: %s", node.kind, pprint.pformat(details))
    name = details.get("name", {}).get("value", "Unknown")
    raw_fields = details.get("fields", [])
    raw_description = details.get("description") or {}
    description = raw_description.get("value")
    directives: typing.Dict[str, typing.List[Directive]] = {}

    fields: typing.List[Field] = []
    for field in raw_fields:
        parsed = parse_field(field, parent=name)
        fields.append(parsed)
        if parsed.directives:
            directives[parsed.name] = parsed.directives

    return ObjectType(
        name=name, fields=fields, directives=directives, description=description
    )


def parse_schema(
    type_defs: typing.Iterable[typing.Union[str, DocumentNode]]
) -> typing.Dict[str, ObjectType]:
    document = concat_documents(type_defs)
    types: typing.Dict[str, ObjectType] = {}

    for definition in document.definitions:
        node = parse_node(definition)
        if node.name in types:
            types[node.name].fields.extend(node.fields)
            types[node.name].directives.update(node.directives)
        else:
            types[node.name] = node

    return types


computed_field_template = """\
    @abc.abstractmethod
    async def {field.name}(
        self,
        info: cannula.ResolveInfo,
{rendered_args}) -> typing.Awaitable[{field.value}]:
        ...

"""

required_field_template = """\
    {field.name}: {field.value}
"""

optional_field_template = """\
    {field.name}: typing.Optional[{field.value}] = {field.default!r}
"""

object_dict_fields = """\
    {field.name}: {field_type}
"""

object_template = """\
@dataclasses.dataclass
class {obj.name}TypeBase(abc.ABC):
    __typename = "{obj.name}"

{rendered_base_fields}
{rendered_computed}
class {obj.name}TypeDict(typing.TypedDict):
{rendered_dict_fields}

{obj.name}Type = typing.Union[{obj.name}TypeBase, {obj.name}TypeDict]
"""

function_args_template = """\
        {arg.name}: {arg_type}{default},
"""

function_template = """\
class {field.func_name}(typing.Protocol):
    def __call__(
        self,
        info: cannula.ResolveInfo,
{rendered_args}) -> typing.Awaitable[{field.value}]:
        ...
"""

operation_field_template = """\
    {field.name}: NotRequired[{field.func_name}]
"""

operation_template = """\
class RootType(typing.TypedDict):
{rendered_fields}"""

base_template = """\
from __future__ import annotations

import abc
import dataclasses
import typing

from typing_extensions import NotRequired

import cannula


{rendered_items}"""


def render_computed_field(field: Field) -> str:
    rendered_args = "".join(render_function_args(arg) for arg in field.args)
    rendered_args = f"{rendered_args}    "
    return computed_field_template.format(field=field, rendered_args=rendered_args)


def render_field(field: Field) -> str:
    if field.required:
        return required_field_template.format(field=field)
    return optional_field_template.format(field=field)


def render_dict_field(field: Field) -> str:
    field_type = field.value if field.required else f"NotRequired[{field.value}]"
    return object_dict_fields.format(field=field, field_type=field_type)


def render_object(obj: ObjectType) -> str:
    non_computed: typing.List[Field] = []
    computed: typing.List[Field] = []
    for field in obj.fields:
        if field.is_computed:
            computed.append(field)
        else:
            non_computed.append(field)

    rendered_computed = "".join([render_computed_field(f) for f in computed])
    rendered_base_fields = "".join([render_field(f) for f in non_computed])
    rendered_dict_fields = "".join([render_dict_field(f) for f in obj.fields])
    return object_template.format(
        obj=obj,
        rendered_computed=rendered_computed,
        rendered_base_fields=rendered_base_fields,
        rendered_dict_fields=rendered_dict_fields,
    )


def ast_for_class_field(field: Field) -> ast.AnnAssign:
    field_type = field.value if field.required else f"Optional[{field.value}]"
    field_type = ast_for_name(field_type)
    default = field.default
    if not field.required and default is None:
        default = ast_for_name("None")
    return ast_for_annotation_assignment(
        field.name, annotation=field_type, default=default
    )


def ast_for_dict_field(field: Field) -> ast.AnnAssign:
    field_type = field.value if field.required else f"NotRequired[{field.value}]"
    field_type = ast_for_name(field_type)
    return ast_for_annotation_assignment(field.name, annotation=field_type)


def ast_for_operation_field(field: Field) -> ast.AnnAssign:
    field_type = (
        field.func_name if field.required else f"NotRequired[{field.func_name}]"
    )
    field_type = ast_for_name(field_type)
    return ast_for_annotation_assignment(field.name, annotation=field_type)


def ast_for_object(obj: ObjectType) -> typing.List[ast.stmt]:
    non_computed: typing.List[Field] = []
    computed: typing.List[Field] = []
    for field in obj.fields:
        if field.is_computed:
            computed.append(field)
        else:
            non_computed.append(field)

    klass_name = f"{obj.name}TypeBase"
    dict_name = f"{obj.name}TypeDict"
    type_name = f"{obj.name}Type"

    klass_fields = [ast_for_class_field(f) for f in non_computed]
    computed_fields = [render_computed_field_ast(f) for f in computed]
    dict_fields = [ast_for_dict_field(f) for f in obj.fields]
    return [
        ast.ClassDef(
            name=klass_name,
            body=[*klass_fields, *computed_fields],
            bases=[ast_for_name("BaseModel")],
            keywords=[],
            decorator_list=[],
        ),
        ast.ClassDef(
            name=dict_name,
            body=dict_fields,
            bases=[ast_for_name("TypedDict")],
            keywords=[],
            decorator_list=[],
        ),
        ast_for_assign(
            type_name,
            ast_for_union_subscript(klass_name, dict_name),
        ),
    ]


def render_function_args(arg: Argument) -> str:
    if arg.required:
        default = f" = {arg.default!r}" if arg.default else ""
        return function_args_template.format(
            arg=arg, arg_type=arg.type, default=default
        )

    arg_type = f"typing.Optional[{arg.type}]"
    default = f" = {arg.default!r}"

    return function_args_template.format(arg=arg, arg_type=arg_type, default=default)


def render_function(field: Field) -> str:
    rendered_args = "".join(render_function_args(arg) for arg in field.args)
    rendered_args = f"{rendered_args}    "
    return function_template.format(field=field, rendered_args=rendered_args)


def render_operation_field(field: Field) -> str:
    return operation_field_template.format(field=field)


def render_operation(fields: typing.List[Field]) -> str:
    rendered_fields = "".join([render_operation_field(f) for f in fields])
    return operation_template.format(
        rendered_fields=rendered_fields,
    )


def ast_for_operation(field: Field) -> ast.ClassDef:
    func = render_operation_field_ast(field)
    return ast.ClassDef(
        name=field.func_name,
        body=[func],
        bases=[ast_for_name("Protocol")],
        keywords=[],
        decorator_list=[],
    )


def ast_for_root_type(fields: typing.List[Field]) -> ast.ClassDef:
    dict_fields = [ast_for_operation_field(f) for f in fields]
    return ast.ClassDef(
        name="RootType",
        body=dict_fields,
        bases=[ast_for_name("TypedDict")],
        keywords=[],
        decorator_list=[],
    )


def render_file(
    type_defs: typing.Iterable[typing.Union[str, DocumentNode]],
    path: pathlib.Path,
    dry_run: bool = False,
) -> None:
    parsed = parse_schema(type_defs)

    object_types: typing.List[ObjectType] = []
    operation_fields: typing.List[Field] = []
    for obj in parsed.values():
        if obj.name in ["Query", "Mutation", "Subscription"]:
            for field in obj.fields:
                operation_fields.append(field)
        else:
            object_types.append(obj)

    object_types.sort(key=lambda o: o.name)
    objects = [render_object(obj) for obj in object_types]

    operation_fields.sort(key=lambda f: f.name)
    operations = render_operation(operation_fields)
    functions = [render_function(field) for field in operation_fields]

    rendered_objects = "\n\n".join(objects + functions)
    rendered_items = f"{rendered_objects}\n\n{operations}"
    content = base_template.format(
        rendered_items=rendered_items,
    )

    if dry_run:
        LOG.info(f"DRY_RUN would produce: \n{content}")
        return

    with open(path, "w") as output:
        output.writelines(content)


def render_ast(
    type_defs: typing.Iterable[typing.Union[str, DocumentNode]],
    path: pathlib.Path,
    dry_run: bool = False,
) -> None:
    parsed = parse_schema(type_defs)

    object_types: typing.List[ObjectType] = []
    operation_fields: typing.List[Field] = []
    for obj in parsed.values():
        if obj.name in ["Query", "Mutation", "Subscription"]:
            for field in obj.fields:
                operation_fields.append(field)
        else:
            object_types.append(obj)

    root = ast.Module(body=[], type_ignores=[])
    root.body.append(ast_for_import_from("__future__", ["annotations"]))
    root.body.append(ast_for_import("abc"))
    root.body.append(ast_for_import("typing"))
    root.body.append(ast_for_import("cannula"))
    root.body.append(ast_for_import_from("pydantic", ["BaseModel"]))
    root.body.append(
        ast_for_import_from(
            "typing",
            [
                "Awaitable",
                "List",
                "Optional",
                "Protocol",
                "TypedDict",
                "Union",
            ],
        )
    )
    root.body.append(ast_for_import_from("typing_extensions", ["NotRequired"]))

    object_types.sort(key=lambda o: o.name)
    for obj in object_types:
        root.body.extend(ast_for_object(obj))

    operation_fields.sort(key=lambda f: f.name)
    root.body.extend([ast_for_operation(f) for f in operation_fields])

    root.body.append(ast_for_root_type(operation_fields))

    # operations = render_operation(operation_fields)
    # functions = [render_function(field) for field in operation_fields]

    # rendered_objects = "\n\n".join(objects + functions)
    # rendered_items = f"{rendered_objects}\n\n{operations}"
    # content = base_template.format(
    #     rendered_items=rendered_items,
    # )

    LOG.info(f"DRY_RUN would produce: \n{ast.dump(root, indent=4)}")
    if dry_run:
        return

    format_with_ruff(root, path)
