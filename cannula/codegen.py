"""
Code Generation
----------------
"""
import dataclasses
import logging
import pathlib
import pprint
import typing

from graphql import (
    DocumentNode,
    Node,
)

from cannula.schema import concat_documents
from cannula.utils import Directive

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


@dataclasses.dataclass
class Field:
    name: str
    value: str
    description: typing.Optional[str]
    directives: typing.List[Directive]
    default: typing.Any = None
    required: bool = False


@dataclasses.dataclass
class FieldType:
    value: typing.Any
    required: bool = False


@dataclasses.dataclass
class ObjectType:
    name: str
    fields: typing.List[Field]
    directives: typing.Dict[str, typing.List[Directive]]
    description: typing.Optional[str] = None


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


def parse_args(obj: dict) -> typing.Dict[str, typing.Any]:
    args = {}
    raw_args = obj.get("arguments") or []
    for arg in raw_args:
        name = parse_name(arg)
        value = parse_value(arg["value"])
        args[name] = value

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
            value = f'"{value}Type"'

    return FieldType(value=value, required=required)


def parse_directives(field: typing.Dict[str, typing.Any]) -> typing.List[Directive]:
    directives: typing.List[Directive] = []
    for directive in field.get("directives", []):
        name = parse_name(directive)
        args = parse_args(directive)
        directives.append(Directive(name=name, args=args))
    return directives


def parse_default(field: typing.Dict[str, typing.Any]) -> typing.Any:
    default_value = field.get("default_value")
    LOG.debug(default_value)
    if not default_value:
        return None

    return parse_value(default_value)


def parse_field(field: typing.Dict[str, typing.Any]) -> Field:
    name = field["name"]["value"]
    field_type = parse_type(field["type"])
    default = parse_default(field)
    directives = parse_directives(field)

    return Field(
        name=name,
        value=field_type.value,
        description=parse_description(field),
        directives=directives,
        default=default,
        required=field_type.required,
    )


def parse_node(node: Node):
    details = node.to_dict()
    LOG.debug(node.kind)
    LOG.debug("\n%s", pprint.pformat(details))
    name = details.get("name", {}).get("value", "Unknown")
    raw_fields = details.get("fields", [])
    raw_description = details.get("description") or {}
    description = raw_description.get("value")
    directives: typing.Dict[str, typing.List[Directive]] = {}

    fields: typing.List[Field] = []
    for field in raw_fields:
        parsed = parse_field(field)
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
        else:
            types[node.name] = node

    return types


required_field_template = """\
    {field.name}: {field.value}
"""


optional_field_template = """\
    {field.name}: typing.Optional[{field.value}] = {field.default!r}
"""


object_template = """\
@dataclasses.dataclass
class {obj.name}Type(cannula.BaseMixin):
    __typename = "{obj.name}"
    __directives__ = {obj.directives!r}

{rendered_fields}"""

base_template = """\
import typing
import dataclasses

import cannula


{rendered_items}"""


def render_field(field: Field) -> str:
    if field.required:
        return required_field_template.format(field=field)
    return optional_field_template.format(field=field)


def render_file(
    type_defs: typing.Iterable[typing.Union[str, DocumentNode]],
    path: pathlib.Path,
    dry_run: bool = False,
) -> None:
    parsed = parse_schema(type_defs)

    items = []
    for obj in parsed.values():
        rendered_fields = "".join([render_field(f) for f in obj.fields])
        items.append(
            object_template.format(
                obj=obj,
                rendered_fields=rendered_fields,
            ),
        )

    rendered_items = "\n\n".join(items)
    content = base_template.format(
        rendered_items=rendered_items,
    )

    if dry_run:
        LOG.info(f"DRY_RUN would produce: \n{content}")
        return

    with open(path, "w") as output:
        output.writelines(content)
