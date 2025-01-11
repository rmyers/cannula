import ast
import dataclasses
import typing

from graphql import GraphQLField


@dataclasses.dataclass
class FieldType:
    value: str | None
    required: bool = False
    of_type: str | None = None
    is_list: bool = False
    is_object_type: bool = False

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

    @property
    def as_ast(self) -> ast.arg:
        is_required = self.required or self.default is not None
        arg_type = self.type if is_required else f"Optional[{self.type}]"
        return ast.arg(arg=self.name, annotation=ast.Name(id=arg_type, ctx=ast.Load()))

    @property
    def as_keyword(self) -> ast.keyword:
        return ast.keyword(self.name, ast.Name(id=self.name, ctx=ast.Load()))


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

    @property
    def relation(self) -> dict:
        return self.metadata.get("relation", {})

    @property
    def required_args(self) -> list[Argument]:
        return [arg for arg in self.args if arg.required]

    @property
    def optional_args(self) -> list[Argument]:
        return [arg for arg in self.args if not arg.required]

    @property
    def positional_args(self) -> list[ast.arg]:
        """Postional args for this field that are required"""
        return [arg.as_ast for arg in self.required_args]

    @property
    def kwonlyargs(self) -> list[ast.arg]:
        """Keyword only args are for this field that are not required"""
        return [arg.as_ast for arg in self.optional_args]

    @property
    def kwdefaults(self) -> list[ast.expr | None]:
        """Defaults constants for the args either provided value or 'None'"""
        return [ast.Constant(value=arg.default) for arg in self.optional_args]

    @property
    def keywords(self) -> list[ast.keyword]:
        """These are used in a function body to call an another function.

        example::

            def myfunction(field_arg, field_kwarg=None):
                return external(field_arg=field_arg, field_kwarg=field_kwarg)
        """
        return [arg.as_keyword for arg in self.args]


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
