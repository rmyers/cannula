"""
Code Generation
----------------
"""
import logging
import pathlib
import pprint
import typing

from graphql import (
    DocumentNode,
    Node,
)

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
        value = f"typing.List[{list_type}]"

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


def has_computed_directive(field: Field) -> bool:
    for directive in field.directives:
        if directive.name == "computed":
            return True

    return False


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
        if field.args or has_computed_directive(field):
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
