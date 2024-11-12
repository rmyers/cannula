"""
Code Generation
----------------
"""

import ast
import collections
import logging
import pathlib
import pprint
import typing

from cannula.scalars import ScalarInterface
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

IMPORTS: typing.DefaultDict[str, set[str]] = collections.defaultdict(set[str])
IMPORTS.update(
    {
        "__future__": set(["annotations"]),
        "abc": set(["ABC", "abstractmethod"]),
        "cannula": set(["ResolveInfo"]),
        "dataclasses": set(["dataclass"]),
        "pydantic": set(["BaseModel"]),
        "typing": set(
            [
                "Any",
                "Awaitable",
                "Sequence",
                "Optional",
                "Protocol",
                # In python < 3.12 pydantic wants us to use typing_extensions
                # "TypedDict",
                "Union",
            ]
        ),
        "typing_extensions": set(["TypedDict", "NotRequired"]),
    }
)

# AST contants for common values
NONE = ast.Constant(value=None)
ELLIPSIS = ast.Expr(value=ast.Constant(value=Ellipsis))


def add_custom_scalar_handlers(scalars: list[ScalarInterface]) -> None:
    for scalar in scalars:
        TYPES[scalar.name] = scalar.input_module.klass
        TYPES[f"{scalar.name}InputType"] = scalar.output_module.klass
        IMPORTS[scalar.input_module.module].add(scalar.input_module.klass)
        IMPORTS[scalar.output_module.module].add(scalar.output_module.klass)


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
    LOG.debug(f"AST for arg: {arg.__dict__}")
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


def parse_description(obj: dict) -> typing.Optional[str]:
    raw_description = obj.get("description") or {}
    is_block = raw_description.get("block", False)
    desc = raw_description.get("value")
    if not desc:
        return None

    # Format blocks with newlines so the doc strings look correct.
    return f"\n{desc}\n" if is_block else desc


def parse_name(obj: dict) -> str:
    raw_name = obj.get("name") or {}
    return raw_name.get("value", "unknown")


def parse_value(obj: dict) -> typing.Any:
    kind = obj["kind"]
    value = obj["value"]

    if func := VALUE_FUNCS.get(kind):
        return func(value)

    return value


def parse_default(obj: typing.Dict[str, typing.Any]) -> typing.Any:
    default_value = obj.get("default_value")
    if not default_value:
        return None

    LOG.debug(f"Default Value: {default_value}")
    return parse_value(default_value)


def parse_args(obj: dict) -> list[Argument]:
    args: list[Argument] = []
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
        value = f"Sequence[{list_type}]"

    if type_obj["kind"] == "named_type":
        name = type_obj["name"]
        value = name["value"]
        if value in TYPES:
            value = TYPES[value]
        else:
            value = f"{value}Type"

    return FieldType(value=value, required=required)


def parse_directives(field: typing.Dict[str, typing.Any]) -> list[Directive]:
    directives: list[Directive] = []
    for directive in field.get("directives", []):
        name = parse_name(directive)
        args = parse_args(directive)
        directives.append(Directive(name=name, args=args))
    return directives


def parse_field(field: typing.Dict[str, typing.Any], parent: str) -> Field:
    LOG.debug("Field: %s", pprint.pformat(field))
    name = parse_name(field)
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
    name = parse_name(details)
    raw_fields = details.get("fields", [])

    description = parse_description(details)
    raw_types = details.get("types", [])
    types = [parse_type(t) for t in raw_types]
    directives: typing.Dict[str, list[Directive]] = {}

    fields: list[Field] = []
    for field in raw_fields:
        parsed = parse_field(field, parent=name)
        fields.append(parsed)
        if parsed.directives:
            directives[parsed.name] = parsed.directives

    return ObjectType(
        name=name,
        kind=node.kind,
        fields=fields,
        directives=directives,
        description=description,
        types=types,
    )


def parse_schema(
    type_defs: typing.Iterable[typing.Union[str, DocumentNode]]
) -> typing.Dict[str, ObjectType]:
    document = concat_documents(type_defs)
    types: typing.Dict[str, ObjectType] = {}

    # First we need to pull out the input types since the default
    # names are different than normal object types.
    for definition in document.definitions:
        node = parse_node(definition)
        if node.kind == "input_object_type_definition":
            TYPES[node.name] = f"{node.name}Input"

    for definition in document.definitions:
        node = parse_node(definition)
        if node.name in types:
            types[node.name].fields.extend(node.fields)
            types[node.name].directives.update(node.directives)
            types[node.name].description = node.description
        else:
            types[node.name] = node

    return types


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


def render_object(obj: ObjectType) -> list[ast.ClassDef | ast.Assign]:
    non_computed: list[Field] = []
    computed: list[Field] = []
    for field in obj.fields:
        if field.is_computed:
            computed.append(field)
        else:
            non_computed.append(field)

    type_name = f"{obj.name}Type"

    type_def = ast_for_assign("__typename", ast_for_constant(obj.name))
    klass_fields = [ast_for_class_field(f) for f in non_computed]
    computed_fields = [render_computed_field_ast(f) for f in computed]

    if obj.description:
        doc_string = ast_for_docstring(obj.description)
        constants = [doc_string, type_def]
    else:
        constants = [type_def]

    return [
        ast.ClassDef(
            name=type_name,
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
        # TODO(rmyers): add option for pydantic
        # ast.ClassDef(
        #     name=type_name,
        #     body=[*constants, *klass_fields, *computed_fields],
        #     bases=[ast_for_name("BaseModel")],
        #     keywords=[],
        #     decorator_list=[],
        #     type_params=[],
        # ),
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
    type_name = f"{obj.name}Type"

    klass_fields = [ast_for_class_field(f) for f in obj.fields]
    return [
        ast.ClassDef(
            name=type_name,
            body=[*klass_fields],
            bases=[ast_for_name("Protocol")],
            keywords=[],
            decorator_list=[],
            # type_params=[],
        )
    ]


def render_union(obj: ObjectType) -> list[ast.ClassDef | ast.Assign]:
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


def render_file(
    type_defs: typing.Iterable[typing.Union[str, DocumentNode]],
    path: pathlib.Path,
    scalars: list[ScalarInterface] = [],
    dry_run: bool = False,
) -> None:
    # first setup custom scalars so the parsed schema includes them
    add_custom_scalar_handlers(scalars)

    parsed = parse_schema(type_defs)

    object_types: list[ObjectType] = []
    interface_types: list[ObjectType] = []
    input_types: list[ObjectType] = []
    union_types: list[ObjectType] = []
    scalar_types: list[ObjectType] = []
    operation_fields: list[Field] = []
    for obj in parsed.values():
        if obj.name in ["Query", "Mutation", "Subscription"]:
            for field in obj.fields:
                operation_fields.append(field)
        elif obj.kind == "scalar_type_definition":
            scalar_types.append(obj)
        elif obj.kind in [
            "object_type_definition",
            "object_type_extension",
        ]:
            object_types.append(obj)
        elif obj.kind == "input_object_type_definition":
            input_types.append(obj)
        elif obj.kind == "interface_type_definition":
            interface_types.append(obj)
        elif obj.kind == "union_type_definition":
            union_types.append(obj)

    root = ast.Module(body=[], type_ignores=[])

    module_imports = list(IMPORTS.keys())
    module_imports.sort()
    for module in module_imports:
        if module == "builtins":
            continue
        root.body.append(ast_for_import_from(module=module, names=IMPORTS[module]))

    for obj in scalar_types:
        if obj.name in TYPES:
            continue
        root.body.append(ast_for_assign(f"{obj.name}Type", ast_for_name("Any")))

    for obj in interface_types:
        root.body.extend(render_interface(obj))

    for obj in input_types:
        root.body.extend(render_input(obj))

    object_types.sort(key=lambda o: o.name)
    for obj in object_types:
        root.body.extend(render_object(obj))

    for obj in union_types:
        root.body.extend(render_union(obj))

    operation_fields.sort(key=lambda f: f.name)
    root.body.extend([ast_for_operation(f) for f in operation_fields])

    if operation_fields:
        root.body.append(ast_for_root_type(operation_fields))

    if dry_run:
        LOG.info(f"DRY_RUN would produce: \n{ast.dump(root, indent=4)}")
        return

    format_with_ruff(root, path)
