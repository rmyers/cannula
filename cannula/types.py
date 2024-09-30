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

    @property
    def is_computed(self) -> bool:
        has_args = bool(self.args)
        has_computed_directive = any(
            directive.name == "computed" for directive in self.directives
        )
        return has_args or has_computed_directive


@dataclasses.dataclass
class FieldType:
    value: typing.Any
    required: bool = False


@dataclasses.dataclass
class ObjectType:
    name: str
    kind: str
    fields: typing.List[Field]
    types: typing.List[FieldType]
    directives: typing.Dict[str, typing.List[Directive]]
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
