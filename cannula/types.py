import ast
import dataclasses
import logging
import typing

import pydantic
from graphql import (
    GraphQLField,
    GraphQLInputField,
    GraphQLInputObjectType,
    GraphQLInterfaceType,
    GraphQLObjectType,
    GraphQLSchema,
    GraphQLUnionType,
    OperationDefinitionNode,
    is_input_object_type,
    is_list_type,
    is_non_null_type,
)
from typing_extensions import Self

from cannula.utils import (
    ast_for_annotation_assignment,
    ast_for_assign,
    ast_for_constant,
    ast_for_docstring,
    ast_for_name,
    ast_for_union_subscript,
    pluralize,
    get_config_var,
)
from cannula.errors import SchemaValidationError

LOG = logging.getLogger(__name__)


class SQLMetadata(pydantic.BaseModel):
    table_name: str
    composite_primary_key: bool = False
    constraints: typing.List[str] = pydantic.Field(default_factory=list)


class FieldMetadata(pydantic.BaseModel):
    primary_key: bool = False
    foreign_key: typing.Optional[str] = None
    nullable: typing.Optional[bool] = None
    index: bool = False
    unique: typing.Optional[bool] = None
    db_column: typing.Optional[str] = None
    args: typing.List[str] = pydantic.Field(default_factory=list)
    where: typing.Optional[str] = None
    raw_sql: typing.Optional[str] = None
    function: typing.Optional[str] = None
    weight: typing.Optional[float] = None


@dataclasses.dataclass
class FieldType:
    value: str
    required: bool = False
    of_type: str = ""
    is_list: bool = False
    is_object_type: bool = False

    def __repr__(self) -> str:
        _type = self.of_type or self.safe_value
        return f"[{_type}]" if self.is_list else _type

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

    @property
    def as_self_keyword(self) -> ast.keyword:
        """Return a keyword arg that references an attribute lookup."""
        return ast.keyword(
            self.name,
            ast.Attribute(
                value=ast.Name(id="self", ctx=ast.Load()),
                attr=self.name,
                ctx=ast.Load(),
            ),
        )


@dataclasses.dataclass
class Directive:
    name: str
    args: typing.List[Argument]

    def to_dict(self) -> dict:
        return {arg.name: arg.value for arg in self.args}


@dataclasses.dataclass
class Field:
    field: GraphQLField
    parent: str
    name: str
    field_type: FieldType
    args: typing.List[Argument]
    related_args: typing.List[Argument] = dataclasses.field(default_factory=list)
    directives: typing.List[Directive] = dataclasses.field(default_factory=list)
    default: typing.Any = None
    computed: bool = False
    fk_field: typing.Optional["Field"] = None

    @classmethod
    def from_field(
        cls,
        name: str,
        parent: str,
        field: GraphQLField,
        field_type: FieldType,
        args: typing.Optional[typing.List[Argument]] = None,
        related_args: typing.Optional[typing.List[Argument]] = None,
        directives: typing.Optional[typing.List[Directive]] = None,
        fk_field: typing.Optional["Field"] = None,
    ) -> "Field":
        args = args or []
        related_args = related_args or []
        return cls(
            field=field,
            parent=parent,
            name=name,
            field_type=field_type,
            args=args,
            related_args=related_args,
            directives=directives or [],
            fk_field=fk_field,
        )

    def __repr__(self) -> str:
        return f"Field<{self.parent}.{self.name}>"

    @property
    def description(self) -> typing.Optional[str]:
        return self.field.description

    @property
    def type(self) -> str:
        return self.field_type.type

    @property
    def required(self) -> bool:
        return self.field_type.required

    @property
    def metadata(self) -> FieldMetadata:
        return self.field.extensions.get("field_meta", FieldMetadata())

    @property
    def connector(self) -> typing.Optional["ConnectDirective"]:
        return self.field.extensions.get("connector")

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
        return has_args or self.field_type.is_object_type

    @property
    def relation_method(self) -> str:
        if self.fk_field is not None:
            if self.field_type.is_list:
                raise SchemaValidationError(
                    f"{self} is related via {self.fk_field} but {self.field_type} is a list. "
                    f"Either change the reponse type to be singular or provide 'where' and 'args' to retrieve data."
                )
            return "get_model_by_pk"
        return f"{self.parent.lower()}_{self.name}"

    @property
    def relation_context_attr(self) -> str:
        """Gets the context var for the related datasource"""
        if self.connector:
            target = self.connector.source
        else:
            target = pluralize(self.field_type.of_type)
        return f"info.context.{target}"

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

            def myfunction(self, field_arg, field_kwarg=None):
                return external(id=self.id, field_arg=field_arg, field_kwarg=field_kwarg)
        """
        related = [arg.as_self_keyword for arg in self.related_args]
        defined_args = [arg.as_keyword for arg in self.args]
        return related + defined_args

    @property
    def related_keywords(self) -> list[ast.keyword]:
        """These are used in a function body to include related args in the query.

        example::

            def myfunction(self, id: str, field_arg: str):
                return self.db_query(text('user_id = :id AND field :field_arg'), id=id, field_arg=field_arg)
        """
        related = [arg.as_keyword for arg in self.related_args]
        defined_args = [arg.as_keyword for arg in self.args]
        return related + defined_args

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

    def validate_field_metadata(self):
        if self.field_type.required and self.metadata.nullable:
            raise SchemaValidationError(
                f"Field '{self.name}' is marked as non-null in GraphQL schema, "
                "but metadata specifies nullable=true. Remove the nullable metadata "
                "or update the GraphQL schema."
            )


@dataclasses.dataclass
class ObjectType:
    """Container for type information and metadata"""

    type_def: GraphQLObjectType
    name: str
    py_type: str
    fields: list[Field]
    related_fields: list[Field] = dataclasses.field(default_factory=list)

    @property
    def description(self) -> typing.Optional[str]:
        return self.type_def.description

    @property
    def sqlmetadata(self) -> typing.Optional[SQLMetadata]:
        return self.type_def.extensions.get("sql_metadata")

    @property
    def db_table(self) -> typing.Optional[str]:
        if self.sqlmetadata:
            return self.sqlmetadata.table_name

        return None

    @property
    def is_db_type(self) -> bool:
        return bool(self.db_table)

    @property
    def db_type(self) -> str:
        return self.type_def.extensions.get("db_type", f"DB{self.name}")

    @property
    def context_attr(self) -> str:
        """Pluralized name used for the attribute on the context object."""
        return pluralize(self.name)


@dataclasses.dataclass
class InterfaceType:
    node: GraphQLInterfaceType
    name: str
    py_type: str
    fields: typing.List[Field]
    metadata: typing.Dict[str, typing.Any]

    @property
    def description(self) -> typing.Optional[str]:
        return self.node.description

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
            type_params=[],  # type: ignore
        )


@dataclasses.dataclass
class UnionType:
    node: GraphQLUnionType
    name: str
    py_type: str
    types: typing.List[FieldType]

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

    @property
    def description(self) -> typing.Optional[str]:
        return self.node.description

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
            type_params=[],  # type: ignore
        )


@dataclasses.dataclass
class Variable:
    name: str
    value: str
    required: bool
    is_list: bool
    default: typing.Any = None

    def coerce_variable(self, variable):
        if self.value == "Int":
            return int(variable)
        elif self.value == "Float":
            return float(variable)
        elif self.value == "Boolean":
            return variable.lower() in ("true", "1", "yes")
        elif self.value == "ID":
            return str(variable)
        else:
            # Could extend this to handle custom scalars from schema
            return variable


class OperationModel:
    """
    A wrapper around a Pydantic model for GraphQL operation variables.
    Provides validation and type conversion for GraphQL operation inputs.
    """

    _input_models: typing.Dict[str, typing.Any]

    def __init__(
        self,
        name: str,
        operation_type: str,
        variables: dict[str, Variable],
        node: OperationDefinitionNode,
        schema: GraphQLSchema,
    ):
        self.name = name
        self.operation_type = operation_type
        self.variable_types = variables
        self.node = node
        self.schema = schema
        self._model = self._create_pydantic_model()

    @property
    def is_mutation(self) -> bool:
        return self.operation_type == "mutation"

    @property
    def template_path(self) -> str:
        template_type = "_form" if self.is_mutation else ""
        return f"{self.name}{template_type}.html"

    @property
    def mutation_result_template(self) -> str:
        return f"{self.name}_result.html"

    def _create_pydantic_model(self) -> typing.Type[pydantic.BaseModel]:
        """
        Create a Pydantic model from the GraphQL variable definitions.
        """
        fields: dict[str, typing.Any] = {}

        for var_name, var_type in self.variable_types.items():
            python_type = self._graphql_to_python_type(var_type)

            # Create field with proper type annotation
            if var_type.required:
                fields[var_name] = (python_type, var_type.default)
            else:
                fields[var_name] = (typing.Optional[python_type], var_type.default)

        # Create the model class
        model_name = f"{self.name.title()}Variables"
        model = pydantic.create_model(model_name, **fields)

        # Add validation methods to the model
        self._add_validators(model)

        return model

    def _graphql_to_python_type(self, var: Variable) -> typing.Any:
        """
        Convert a GraphQL type to a Python type.
        Recursively handles input types.
        """
        schema_type = self.schema.get_type(var.value)
        if not schema_type:
            return str

        # Handle input object types
        if is_input_object_type(schema_type):
            # Create a nested model for the input type
            input_model = self._create_input_type_model(var.value)
            base_type = input_model
        else:
            # Use the Python type from extensions for scalars
            base_type = schema_type.extensions.get("py_type", str)

        if var.is_list:
            return typing.List[base_type]  # type: ignore
        return base_type

    def _create_input_type_model(
        self, type_name: str
    ) -> typing.Type[pydantic.BaseModel]:
        """
        Create a Pydantic model for an input type.
        """
        # Check if we've already created this model
        if hasattr(self, "_input_models") and type_name in self._input_models:
            return self._input_models[type_name]

        # Initialize input model cache if needed
        if not hasattr(self, "_input_models"):
            self._input_models = {}

        # Get the type definition
        type_def = self.schema.get_type(type_name)
        if not type_def or not is_input_object_type(type_def):
            raise AttributeError(f"{type_name} is not a input type")

        type_def = typing.cast(GraphQLInputObjectType, type_def)

        # Create fields for the model
        fields: dict[str, typing.Any] = {}
        for field_name, field_def in type_def.fields.items():
            input_def = typing.cast(GraphQLInputField, field_def)
            # Create a temporary Variable for this field to reuse _graphql_to_python_type
            field_var = Variable(
                name=field_name,
                value=self._get_named_type_name(input_def.type),
                required=self._is_required_type(input_def.type),
                is_list=self._is_list_type(input_def.type),
            )

            field_type = self._graphql_to_python_type(field_var)

            # Add the field with proper required status
            if field_var.required:
                fields[field_name] = (field_type, ...)
            else:
                fields[field_name] = (typing.Optional[field_type], None)  # type: ignore

        # Create the model
        model = pydantic.create_model(type_name, **fields)

        # Cache the model
        self._input_models[type_name] = model

        return model

    def _get_named_type_name(self, field_type) -> str:
        """Extract the name of the innermost named type."""
        if hasattr(field_type, "of_type"):
            return self._get_named_type_name(field_type.of_type)
        return field_type.name if hasattr(field_type, "name") else str(field_type)

    def _is_required_type(self, field_type) -> bool:
        """Check if the field type is non-null (required)."""
        return is_non_null_type(field_type)

    def _is_list_type(self, field_type) -> bool:
        """Check if the field type is a list, handling non-null wrappers."""
        if is_non_null_type(field_type):
            return self._is_list_type(field_type.of_type)
        return is_list_type(field_type)

    def _add_validators(self, model: typing.Type[pydantic.BaseModel]) -> None:
        """
        Add validation methods to the model.
        """
        # This could be expanded to add GraphQL-specific validations
        pass

    def parse_and_validate(self, data: dict[str, typing.Any]) -> dict[str, typing.Any]:
        """
        Parse and validate input data against the model.
        Returns a dictionary with validated and type-converted values.
        """
        try:
            # Create a model instance with the data
            model_instance = self._model(**data)
            # Return the model as a dict
            return model_instance.model_dump()
        except Exception as e:
            LOG.error(f"Validation error for operation {self.name}: {str(e)}")
            raise ValueError(f"Invalid input data for operation {self.name}: {str(e)}")

    def __repr__(self) -> str:
        return f"OperationModel(name='{self.name}', type='{self.operation_type}')"


@dataclasses.dataclass
class Operation:
    """Represents a parsed GraphQL operation with its metadata"""

    name: str
    operation_type: str  # 'query' or 'mutation'
    variable_types: typing.Dict[str, Variable]
    node: OperationDefinitionNode
    schema: GraphQLSchema

    def __post_init__(self):
        # Initialize the OperationModel
        self._model = OperationModel(
            name=self.name,
            operation_type=self.operation_type,
            variables=self.variable_types,
            node=self.node,
            schema=self.schema,
        )

    @property
    def is_mutation(self) -> bool:
        return self.operation_type == "mutation"

    @property
    def template_path(self) -> str:
        template_type = "_form" if self.is_mutation else ""
        return f"{self.name}{template_type}.html"

    @property
    def mutation_result_template(self) -> str:
        return f"{self.name}_result.html"

    def validate_variables(
        self, data: typing.Dict[str, typing.Any]
    ) -> typing.Dict[str, typing.Any]:
        """
        Validate and convert input data using the Pydantic model.

        Args:
            data: Dictionary of input variables from form data or query parameters

        Returns:
            A dictionary with validated and type-converted values
        """
        return self._model.parse_and_validate(data)


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


class HTTPHeaderMapping(pydantic.BaseModel):
    name: str
    from_header: typing.Optional[str] = pydantic.Field(
        default=None,
        # This allows us to have schema set 'from' and still allow us to set
        # 'from_header' in Python since 'from' would be a syntax error
        validation_alias=pydantic.AliasChoices("from_header", "from"),
        serialization_alias="from_header",
    )
    value: typing.Optional[str] = None

    @property
    def config_vars(self) -> typing.Optional[str]:
        """Return a list of variable names used '$config.my_url' -> 'my_url'"""
        return get_config_var(self.value)


class ConnectHTTP(pydantic.BaseModel):
    GET: typing.Optional[str] = None
    POST: typing.Optional[str] = None
    PUT: typing.Optional[str] = None
    PATCH: typing.Optional[str] = None
    DELETE: typing.Optional[str] = None
    headers: typing.Optional[typing.List[HTTPHeaderMapping]] = None
    body: typing.Optional[str] = None

    _method: str = ""
    _path: str = ""

    @pydantic.model_validator(mode="after")
    def check_method(self) -> Self:
        attrs = ["GET", "POST", "PUT", "PATCH", "DELETE"]
        found = list(filter(None, [v for v in attrs if getattr(self, v)]))
        _count = len(found)
        if _count > 1:
            raise ValueError(
                f"@connect directive can only use one method you set {found}"
            )
        if not _count:
            raise ValueError(
                "@connect directive must provide one of 'GET,POST,PUT,PATCH,DELETE'"
            )
        self._method = found[0]
        self._path = getattr(self, found[0])
        return self

    @property
    def method(self) -> str:
        return self._method

    @property
    def path(self) -> str:
        return self._path

    @property
    def config_vars(self) -> typing.Set[str]:
        """Return a list of variable names used '$config.my_url' -> 'my_url'"""
        return set(filter(None, [header.config_vars for header in self.headers or []]))


class SourceHTTP(pydantic.BaseModel):
    baseURL: str
    headers: typing.List[HTTPHeaderMapping] = pydantic.Field(default_factory=list)

    @property
    def config_vars(self) -> typing.Set[str]:
        """Return a list of variable names used '$config.my_url' -> 'my_url'"""
        vars = set(filter(None, [header.config_vars for header in self.headers]))
        base_url_var = get_config_var(self.baseURL)
        if base_url_var:
            vars.add(base_url_var)
        return vars


class ConnectDirective(pydantic.BaseModel):
    field: str
    parent: str
    source: typing.Optional[str] = None
    http: ConnectHTTP
    selection: str
    entity: bool = False

    @property
    def datasource_name(self) -> str:
        prefix = (
            self.source.title()
            if self.source
            else f"{self.parent.title()}{self.field.title()}"
        )
        return f"{prefix}HTTPDatasource"

    @property
    def config_vars(self) -> typing.Set[str]:
        """Return a list of variable names used '$config.my_url' -> 'my_url'"""
        return self.http.config_vars


class SourceDirective(pydantic.BaseModel):
    name: str
    http: SourceHTTP

    def __hash__(self):
        return hash(self.name)

    @property
    def datasource_name(self) -> str:
        return f"{self.name.title()}HTTPDatasource"

    @property
    def config_vars(self) -> typing.Set[str]:
        """Return a list of variable names used '$config.my_url' -> 'my_url'"""
        return self.http.config_vars


@dataclasses.dataclass
class TemplateField:
    """Represents a field in a GraphQL selection set for template rendering."""

    name: str
    path: str
    label: str
    type_name: str
    is_list: bool = False
    class_name: str = ""
    nested_fields: list["TemplateField"] = dataclasses.field(default_factory=list)
    original_field: typing.Optional[Field] = None

    @classmethod
    def from_schema_field(
        cls, field_name: str, path: str, schema_field: typing.Optional[Field] = None
    ) -> "TemplateField":
        """Create a TemplateField from a schema field."""
        return cls(
            name=field_name,
            path=path,
            label=field_name.replace("_", " ").title(),
            type_name=schema_field.field_type.of_type if schema_field else "String",
            is_list=schema_field.field_type.is_list if schema_field else False,
            class_name=path.replace(".", "-"),
            original_field=schema_field,
        )
