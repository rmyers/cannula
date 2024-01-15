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

LOG = logging.getLogger(__name__)

TYPES = {
    "Boolean": "bool",
    "Float": "float",
    "ID": "str",
    "Int": "int",
    "String": "str",
}


@dataclasses.dataclass
class Field:
    name: str
    value: str
    description: typing.Optional[str]
    default: typing.Any = None
    required: bool = False


@dataclasses.dataclass
class FieldType:
    value: typing.Any
    default: typing.Any = None
    required: bool = False


@dataclasses.dataclass
class ObjectType:
    name: str
    fields: typing.List[Field]
    description: typing.Optional[str] = None


def parse_description(obj: dict) -> typing.Optional[str]:
    raw_description = obj.get("description") or {}
    return raw_description.get("value")


def parse_type(type_obj: dict) -> FieldType:
    required = False
    value = None
    default = type_obj.get("default_value")

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
            value = f'"{value}"'

    return FieldType(value=value, required=required, default=default)


def parse_field(field: typing.Dict[str, typing.Any]) -> Field:
    name = field["name"]["value"]
    field_type = parse_type(field["type"])

    return Field(
        name=name,
        value=field_type.value,
        description=parse_description(field),
        default=field_type.default,
        required=field_type.required,
    )


def parse_node(node: Node):
    details = node.to_dict()
    LOG.debug("\n%s", pprint.pformat(details))
    name = details.get("name", {}).get("value", "Unknown")
    raw_fields = details.get("fields", [])
    raw_description = details.get("description") or {}
    description = raw_description.get("value")

    fields: typing.List[Field] = []
    for field in raw_fields:
        fields.append(parse_field(field))

    return ObjectType(name=name, fields=fields, description=description)


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


required_field_template = """
        (
            "{field.name}",
            {field.value},
        ),"""


optional_field_template = """
        (
            "{field.name}",
            typing.Optional[{field.value}],
            dataclasses.field(default={field.default})
        ),"""


object_template = """\
{obj.name} = dataclasses.make_dataclass(
    "{obj.name}",
    fields=[{rendered_fields}
    ],
)
"""

base_template = """\
import typing
import dataclasses


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
