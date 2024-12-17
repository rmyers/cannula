import collections
import logging
import typing
import pprint

from cannula.scalars import ScalarInterface
from graphql import (
    DocumentNode,
    GraphQLNamedType,
    GraphQLSchema,
    GraphQLUnionType,
    is_input_object_type,
    is_interface_type,
    is_object_type,
    is_union_type,
)

from cannula.schema import build_and_extend_schema
from cannula.codegen.types import (
    Argument,
    Directive,
    Field,
    FieldType,
    ObjectType,
    UnionType,
)

LOG = logging.getLogger(__name__)

_IMPORTS: typing.DefaultDict[str, set[str]] = collections.defaultdict(set[str])
_IMPORTS.update(
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
VALUE_FUNCS = {
    "boolean_value": lambda value: value in ["true", "True"],
    "int_value": lambda value: int(value),
    "float_value": lambda value: float(value),
}

TypeMap: typing.TypeAlias = typing.Dict[str, GraphQLNamedType]


class Schema:

    object_types: list[ObjectType]
    interface_types: list[ObjectType]
    input_types: list[ObjectType]
    union_types: list[UnionType]
    scalar_types: list[ObjectType]
    operation_fields: list[Field]
    _schema: GraphQLSchema
    _types: TypeMap

    def __init__(
        self,
        type_defs: typing.Iterable[typing.Union[str, DocumentNode]],
        scalars: typing.List[ScalarInterface],
    ):
        self._schema = build_and_extend_schema(
            type_defs,
            scalars,
            {"imports": _IMPORTS},
        )
        self._set_object_types()
        self._types = self._schema.type_map
        self.object_types = []
        self.input_types = []
        self.interface_types = []
        self.union_types = []
        self.scalar_types = []
        self.operation_fields = []
        self._parse_definitions()

    def _set_object_types(self):
        # Set all the py_types for schema types
        for name, definition in self._schema.type_map.items():
            is_private = name.startswith("__")

            if is_input_object_type(definition):
                definition.extensions["py_type"] = f"{name}Input"

            elif is_union_type(definition):
                definition.extensions["py_type"] = name

            elif is_object_type(definition) and not is_private:
                definition.extensions["py_type"] = f"{name}Type"

            elif is_interface_type(definition):
                definition.extensions["py_type"] = name

    def _parse_definitions(self):
        # Parse the object types and sort them
        for name, definition in self._schema.type_map.items():
            is_private = name.startswith("__")
            is_operation = name in ["Query", "Mutation", "Subscription"]

            if is_input_object_type(definition):
                self.input_types.append(self.parse_node(definition))

            elif is_interface_type(definition):
                self.interface_types.append(self.parse_node(definition))

            elif is_union_type(definition):
                _union = typing.cast(GraphQLUnionType, definition)
                self.union_types.append(self.parse_union(_union))

            elif is_operation:
                operation = self.parse_node(definition)
                self.operation_fields.extend(operation.fields)

            elif is_object_type(definition) and not is_private:
                self.object_types.append(self.parse_node(definition))

        for d in self._schema.directives:
            if d.ast_node:
                pprint.pprint(d.ast_node.to_dict())

        self.object_types.sort(key=lambda o: o.name)
        self.operation_fields.sort(key=lambda o: o.name)

    def parse_description(self, obj: dict) -> typing.Optional[str]:
        raw_description = obj.get("description") or {}
        is_block = raw_description.get("block", False)
        desc = raw_description.get("value")
        if not desc:
            return None

        # Format blocks with newlines so the doc strings look correct.
        return f"\n{desc}\n" if is_block else desc

    def parse_name(self, obj: dict) -> str:
        raw_name = obj.get("name") or {}
        return raw_name.get("value", "unknown")

    def parse_value(self, obj: dict) -> typing.Any:
        kind = obj["kind"]
        value = obj["value"]

        if func := VALUE_FUNCS.get(kind):
            return func(value)

        return value

    def parse_default(self, obj: typing.Dict[str, typing.Any]) -> typing.Any:
        default_value = obj.get("default_value")
        if not default_value:
            return None

        # LOG.debug(f"Default Value: {default_value}")
        return self.parse_value(default_value)

    def parse_args(self, obj: dict) -> list[Argument]:
        args: list[Argument] = []
        raw_args = obj.get("arguments") or []
        for arg in raw_args:
            name = self.parse_name(arg)
            arg_type = FieldType(value=None, required=False)
            raw_type = arg.get("type")
            if raw_type:
                arg_type = self.parse_type(raw_type)
            value = None
            raw_value = arg.get("value")
            if raw_value:
                value = self.parse_value(raw_value)
            default = self.parse_default(arg)
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

    def parse_type(self, type_obj: dict) -> FieldType:
        required = False
        value = None

        if type_obj["kind"] == "non_null_type":
            required = True
            value = self.parse_type(type_obj["type"]).value

        if type_obj["kind"] == "list_type":
            list_type = self.parse_type(type_obj["type"]).value
            value = f"Sequence[{list_type}]"

        if type_obj["kind"] == "named_type":
            name = type_obj["name"]
            value = name["value"]
            if value in self._types:
                value = self._types[value].extensions["py_type"]

        return FieldType(value=value, required=required)

    def parse_directives(self, field: typing.Dict[str, typing.Any]) -> list[Directive]:
        directives: list[Directive] = []
        for directive in field.get("directives", []):
            name = self.parse_name(directive)
            args = self.parse_args(directive)
            directives.append(Directive(name=name, args=args))
        return directives

    def parse_field(self, field: typing.Dict[str, typing.Any], parent: str) -> Field:
        # LOG.debug("Field: %s", pprint.pformat(field))
        name = self.parse_name(field)
        field_type = self.parse_type(field["type"])
        default = self.parse_default(field)
        directives = self.parse_directives(field)
        args = self.parse_args(field)
        func_name = f"{name}{parent}"

        return Field(
            name=name,
            value=field_type.value,
            func_name=func_name,
            description=self.parse_description(field),
            directives=directives,
            args=args,
            default=default,
            required=field_type.required,
        )

    def parse_union(self, node: GraphQLUnionType) -> UnionType:
        assert node.ast_node is not None
        details = node.ast_node.to_dict()
        py_type = node.extensions.get("py_type", node.name)
        description = self.parse_description(details)
        raw_types = details.get("types", [])
        types = [self.parse_type(t) for t in raw_types]

        return UnionType(
            name=node.name,
            py_type=py_type,
            description=description,
            types=types,
        )

    def parse_node(self, node: GraphQLNamedType):
        assert node.ast_node is not None
        details = node.ast_node.to_dict()
        LOG.debug("%s: %s", node.name, pprint.pformat(details))
        name = self.parse_name(details)
        raw_fields = getattr(node, "fields", {})
        py_type = node.extensions.get("py_type", node.name)

        description = self.parse_description(details)
        directives: typing.Dict[str, list[Directive]] = {}

        fields: list[Field] = []
        for field_name, field in raw_fields.items():
            if field_name == "_empty":
                continue
            parsed = self.parse_field(field.ast_node.to_dict(), parent=name)
            fields.append(parsed)
            if parsed.directives:
                directives[parsed.name] = parsed.directives

        return ObjectType(
            name=name,
            py_type=py_type,
            fields=fields,
            directives=directives,
            description=description,
        )


def parse_schema(
    type_defs: typing.Iterable[typing.Union[str, DocumentNode]],
    scalars: typing.List[ScalarInterface],
) -> Schema:
    return Schema(type_defs, scalars)
