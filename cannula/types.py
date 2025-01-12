import ast
import dataclasses
import typing

from graphql import GraphQLField, GraphQLInputObjectType, GraphQLInterfaceType

from cannula.utils import (
    ast_for_annotation_assignment,
    ast_for_assign,
    ast_for_constant,
    ast_for_docstring,
    ast_for_name,
    ast_for_union_subscript,
)


@dataclasses.dataclass
class FieldType:
    value: str
    required: bool = False
    of_type: str = ""
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
        return ast.arg(arg=self.name, annotation=ast_for_name(arg_type))

    @property
    def as_keyword(self) -> ast.keyword:
        return ast.keyword(self.name, ast_for_name(self.name))


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
    def required(self) -> bool:
        return self.field_type.required

    @property
    def operation_name(self) -> str:
        return f"{self.name}{self.parent}"

    @property
    def operation_type(self) -> str:
        return (
            self.operation_name if self.required else f"Optional[{self.operation_name}]"
        )

    @property
    def is_computed(self) -> bool:
        has_args = bool(self.args)
        return has_args or self.computed

    @property
    def relation(self) -> dict:
        return self.metadata.get("relation", {})

    @property
    def relation_method(self) -> str:
        return f"{self.parent.lower()}_{self.name}"

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

    @property
    def as_class_var(self) -> ast.AnnAssign:
        field_type = ast_for_name(self.type)

        # Handle the defaults properly. When the field is required we don't want to
        # set a default value of `None`. But when it is optional we need to properly
        # construct the default using `ast_for_name`.
        default: typing.Optional[ast.expr] = None
        if not self.required:
            default = ast_for_constant(self.default)

        return ast_for_annotation_assignment(
            self.name, annotation=field_type, default=default
        )

    @property
    def as_typed_dict_var(self) -> ast.AnnAssign:
        return ast_for_annotation_assignment(
            self.name,
            # For input types we need to include all fields as required
            # since the resolver will fill in the default values if not provided
            annotation=ast_for_name(self.field_type.safe_value),
        )


@dataclasses.dataclass
class ObjectType:
    name: str
    py_type: str
    fields: typing.List[Field]
    directives: typing.List[Directive]
    description: typing.Optional[str] = None
    defined_scalar_type: bool = False


@dataclasses.dataclass
class InterfaceType:
    node: GraphQLInterfaceType
    name: str
    py_type: str
    fields: typing.List[Field]
    metadata: typing.Dict[str, typing.Any]
    description: typing.Optional[str] = None

    @property
    def as_ast(self) -> ast.ClassDef:
        body: list[ast.stmt] = []
        if self.description:
            body.append(ast_for_docstring(self.description))

        # Add fields as stmts
        for field in self.fields:
            body.append(field.as_class_var)

        return ast.ClassDef(
            name=self.py_type,
            bases=[ast.Name(id="Protocol", ctx=ast.Load())],
            keywords=[],
            body=body,
            decorator_list=[],
            type_params=[],
        )


@dataclasses.dataclass
class UnionType:
    name: str
    py_type: str
    types: typing.List[FieldType]
    description: typing.Optional[str] = None

    @property
    def as_ast(self) -> ast.Assign:
        member_types = [t.safe_value for t in self.types]
        return ast_for_assign(
            self.py_type,
            ast_for_union_subscript(*member_types),
        )


@dataclasses.dataclass
class InputType:
    node: GraphQLInputObjectType
    name: str
    py_type: str
    fields: typing.List[Field]
    metadata: typing.Dict[str, typing.Any]
    description: typing.Optional[str] = None

    @property
    def as_ast(self) -> ast.ClassDef:
        body: list[ast.stmt] = []
        if self.description:
            body.append(ast_for_docstring(self.description))

        # Add fields as stmts
        for field in self.fields:
            body.append(field.as_typed_dict_var)

        return ast.ClassDef(
            name=self.py_type,
            bases=[ast_for_name("TypedDict")],
            keywords=[],
            body=body,
            decorator_list=[],
            type_params=[],
        )


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
