"""
Using the API
=============


"""

import asyncio
import functools
import logging
import inspect
import pathlib
import typing

from cannula.scalars import ScalarInterface
from graphql import (
    DocumentNode,
    GraphQLError,
    GraphQLField,
    GraphQLFieldMap,
    GraphQLObjectType,
    GraphQLScalarType,
    execute,
    ExecutionResult,
    GraphQLSchema,
    parse,
    validate_schema,
    validate,
)

from .context import Context
from .schema import (
    build_and_extend_schema,
    load_schema,
    maybe_parse,
)

LOG = logging.getLogger(__name__)

RootType = typing.TypeVar("RootType", covariant=True)


class ParseResults(typing.NamedTuple):
    document_ast: DocumentNode
    errors: typing.List[GraphQLError] = []


class API(typing.Generic[RootType]):
    """
    Your entry point into the fun filled world of graphql. Just dive right in::

        import cannula

        api = cannula.API(schema='''
            extend type Query {
                hello(who: String): String
            }
        ''')

        @api.resolver('Query')
        def hello(who):
            return f'Hello {who}!'

    :param schema: GraphQL Schema for this resolver. This can either be a str or `pathlib.Path` object.
    :param context: Context class to hold shared state, added to GraphQLResolveInfo object.
    :param middleware: List of middleware to enable.
    :param root_value: Mapping of operation names to resolver functions.
    :param kwargs: Any extra kwargs passed directly to graphql.execute function.
    """

    _schema: typing.Union[str, DocumentNode, pathlib.Path]
    _root_value: typing.Optional[RootType]
    _context: typing.Type[Context]
    _scalars: typing.List[ScalarInterface]
    _kwargs: typing.Dict[str, typing.Any]
    schema: GraphQLSchema
    logger: typing.Optional[logging.Logger]
    level: int

    def __init__(
        self,
        schema: typing.Union[str, DocumentNode, pathlib.Path],
        context: typing.Optional[typing.Type[Context]] = None,
        middleware: typing.List[typing.Any] = [],
        root_value: typing.Optional[RootType] = None,
        scalars: typing.List[ScalarInterface] = [],
        logger: typing.Optional[logging.Logger] = None,
        level: int = logging.DEBUG,
        **kwargs,
    ):
        self._context = context or Context
        self._schema = schema
        self.middleware = middleware
        self._root_value = root_value
        self._scalars = scalars
        self._kwargs = kwargs
        self.logger = logger
        self.level = level
        self.schema = self._build_schema()

    def query(self, field_name: typing.Optional[str] = None) -> typing.Any:
        """Query Resolver

        Short cut to add a resolver for a query, by default it will use the
        name of the function as the `field_name` to be resolved::

            api = cannula.API(schema="type Query { something: String }")

            @api.query
            async def something(parent, info):
                return "hello world"

            @api.query(field_name="something")
            async def some_other_something(parent, info):
                return "override the function name"

        :param field_name: Field name to resolve, by default the function name will be used.
        """
        return self.resolver("Query", field_name)

    def mutation(self, field_name: typing.Optional[str] = None) -> typing.Any:
        """Mutation Resolver

        Short cut to add a resolver for a mutation, by default it will use the
        name of the function as the `field_name` to be resolved::

            api = cannula.API(schema="type Mutation { make_it(name: String): String }")

            @api.mutation
            async def make_it(parent, info, name: str):
                return "hello world"

            @api.mutation(field_name="make_it")
            async def some_other_something(parent, info, name: str):
                return "override the function name"

        :param field_name: Field name to resolve, by default the function name will be used.
        """
        return self.resolver("Mutation", field_name)

    def resolver(
        self, type_name: str, field_name: typing.Optional[str] = None
    ) -> typing.Any:
        """Field Resolver

        Add a field resolver for a given type, by default it will use the
        name of the function as the `field_name` to be resolved::

            api = cannula.API(schema="type Book { name: String }")

            @api.resolver("Book")
            async def name(parent, info):
                return "hello world"

            @api.resolver("Book", field_name="something")
            async def some_other_something(parent, info):
                return "override the function name

        :param type_name: Parent object type name that is being resolved.
        :param field_name: Field name to resolve, by default the function name will be used.
        """

        def decorator(function):
            _name = field_name or function.__name__
            field_def = self._validate_field(type_name=type_name, field_name=_name)
            field_def.resolve = function

        return decorator

    def _find_schema(self) -> typing.List[DocumentNode]:
        schemas: typing.List[DocumentNode] = []

        if isinstance(self._schema, pathlib.Path):
            schemas.extend(load_schema(self._schema))
        else:
            schemas.append(maybe_parse(self._schema))

        return schemas

    def _set_scalars(self, schema: GraphQLSchema) -> GraphQLSchema:
        for scalar in self._scalars:
            object_type = schema.get_type(scalar.name)
            if object_type is None:
                raise Exception(
                    f"Invalid scalar type {scalar.name} did you forget to define it?"
                )

            object_type = typing.cast(GraphQLScalarType, object_type)
            object_type.serialize = scalar.serialize  # type: ignore
            object_type.parse_value = scalar.parse_value  # type: ignore

        return schema

    def _build_schema(self) -> GraphQLSchema:
        schema = build_and_extend_schema(self._find_schema())
        schema = self._set_scalars(schema)

        schema_validation_errors = validate_schema(schema)
        if schema_validation_errors:
            raise Exception(f"Invalid schema: {schema_validation_errors}")

        return schema

    def _validate_field(self, type_name: str, field_name: str) -> GraphQLField:
        object_type = self.schema.get_type(type_name)
        if object_type is None:
            raise Exception(f"Invalid type '{type_name}' in resolver decorator")

        # Need to cast this to object_type to satisfy mypy checks
        object_type = typing.cast(GraphQLObjectType, object_type)
        field_map = typing.cast(GraphQLFieldMap, object_type.fields)
        field_definition = field_map.get(field_name)
        if not field_definition:
            raise Exception(
                f"Invalid field '{type_name}.{field_name}' in resolver decorator"
            )

        return field_definition

    def get_context(self, request) -> typing.Any:
        return self._context.init(request)

    @functools.lru_cache(maxsize=128)
    def _validate(self, document: DocumentNode) -> typing.List[GraphQLError]:
        """Validate the document against the schema and store results in lru_cache."""
        return validate(self.schema, document)

    @functools.lru_cache(maxsize=128)
    def _parse_document(self, document: str) -> ParseResults:
        """Parse and store the document in lru_cache."""
        try:
            document_ast = parse(document)
            return ParseResults(document_ast, [])
        except GraphQLError as err:
            return ParseResults(DocumentNode(), [err])

    async def call(
        self,
        document: typing.Union[DocumentNode, str],
        request: typing.Any = None,
        variables: typing.Optional[typing.Dict[str, typing.Any]] = None,
    ) -> ExecutionResult:
        """Preform a query against the schema.

        This is meant to be called in an asyncio.loop, if you are using a
        web framework that is synchronous use the `call_sync` method.
        """
        if isinstance(document, str):
            document, errors = self._parse_document(document)
            if errors:
                return ExecutionResult(data=None, errors=errors)

        if validation_errors := self._validate(document):
            return ExecutionResult(data=None, errors=validation_errors)

        context = self.get_context(request)
        result = execute(
            schema=self.schema,
            document=document,
            context_value=context,
            variable_values=variables,
            middleware=self.middleware,
            root_value=self._root_value,
            **self._kwargs,
        )
        if inspect.isawaitable(result):
            return await result
        return typing.cast(ExecutionResult, result)

    def call_sync(
        self,
        document: DocumentNode,
        request: typing.Optional[typing.Any] = None,
        variables: typing.Optional[typing.Dict[str, typing.Any]] = None,
    ) -> ExecutionResult:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.call(document, request, variables))
