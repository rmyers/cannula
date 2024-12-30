import dataclasses
import typing

from graphql import GraphQLField


@dataclasses.dataclass
class FieldType:
    value: str | None
    required: bool = False
    of_type: str | None = None

    @property
    def safe_value(self) -> str:
        return self.value or "Any"

    @property
    def type(self) -> str:
        return self.safe_value if self.required else f"Optional[{self.safe_value}]"


@dataclasses.dataclass
class Argument:
    name: str
    type: typing.Any = None
    value: typing.Any = None
    default: typing.Any = None
    required: bool = False


@dataclasses.dataclass
class Directive:
    name: str
    args: typing.List[Argument]


@dataclasses.dataclass
class Field:
    field: GraphQLField
    metadata: typing.Dict[str, typing.Any]
    parent: str
    name: str
    field_type: FieldType
    description: typing.Optional[str]
    args: typing.List[Argument]
    directives: typing.List[Directive] = dataclasses.field(default_factory=list)
    default: typing.Any = None
    computed: bool = False

    @classmethod
    def from_field(
        cls,
        name: str,
        parent: str,
        field: GraphQLField,
        field_type: FieldType,
        metadata: typing.Dict[str, typing.Any],
        args: typing.Optional[typing.List[Argument]] = None,
        directives: typing.Optional[typing.List[Directive]] = None,
    ) -> "Field":
        args = args or []
        meta = metadata.get("metadata", {})
        return cls(
            field=field,
            metadata=meta,
            parent=parent,
            name=name,
            field_type=field_type,
            description=metadata.get("description"),
            computed=meta.get("computed", False),
            args=args,
            directives=directives or [],
        )

    @property
    def type(self) -> str:
        return self.field_type.type

    @property
    def func_name(self) -> str:
        return f"{self.name}{self.parent}"

    @property
    def required(self) -> bool:
        return self.field_type.required

    @property
    def operation_type(self) -> str:
        return self.func_name if self.required else f"Optional[{self.func_name}]"

    @property
    def is_computed(self) -> bool:
        has_args = bool(self.args)
        return has_args or self.computed


@dataclasses.dataclass
class ObjectType:
    name: str
    py_type: str
    fields: typing.List[Field]
    directives: typing.List[Directive]
    description: typing.Optional[str] = None
    defined_scalar_type: bool = False


@dataclasses.dataclass
class UnionType:
    name: str
    py_type: str
    types: typing.List[FieldType]
    description: typing.Optional[str] = None


@dataclasses.dataclass
class OperationField:
    name: str
    value: str
    func_name: str
    description: typing.Optional[str]
    directives: typing.List[Directive]
    args: typing.List[Argument]
    default: typing.Any = None
    required: bool = False
