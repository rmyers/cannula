import dataclasses
import typing


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
    name: str
    value: str
    func_name: str
    description: typing.Optional[str]
    directives: typing.List[Directive]
    args: typing.List[Argument]
    default: typing.Any = None
    required: bool = False
    computed: bool = False

    @property
    def type(self) -> str:
        return self.value if self.required else f"Optional[{self.value}]"

    @property
    def operation_type(self) -> str:
        return self.func_name if self.required else f"Optional[{self.func_name}]"

    @property
    def is_computed(self) -> bool:
        has_args = bool(self.args)
        return has_args or self.computed


@dataclasses.dataclass
class FieldType:
    value: typing.Any
    required: bool = False


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
