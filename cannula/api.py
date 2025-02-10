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

from graphql import (
    DocumentNode,
    GraphQLError,
    GraphQLField,
    GraphQLFieldMap,
    GraphQLObjectType,
    concat_ast,
    execute,
    ExecutionResult,
    GraphQLSchema,
    parse,
    subscribe,
    validate_schema,
    validate,
)
from starlette.applications import Starlette
from starlette.routing import Route

from .context import Context
from .errors import SchemaValidationError
from .handlers.app_router import AppRouter
from .handlers.operations import HTMXHandler
from .handlers.asgi import GraphQLHandler
from .scalars import ScalarInterface
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


class CannulaAPI(typing.Generic[RootType], Starlette):
    """
    Your entry point into the fun filled world of graphql. Just dive right in::

        import cannula

        api = cannula.CannulaAPI(schema='''
            extend type Query {
                hello(who: String): String
            }
        ''')

        @api.resolver('Query')
        def hello(who):
            return f'Hello {who}!'

    Args:
        schema:
            GraphQL Schema for this resolver. This can either be a str or `pathlib.Path` object.
        context:
            Context class to hold shared state, added to GraphQLResolveInfo object.
        middleware:
            List of middleware to enable.
        root_value:
            Mapping of operation names to resolver functions. This can be a TypedDict object
            that is generated by the codegen. Type hints are available if you initialize the
            api with this type like so::

                class MyRootType(TypedDict, total=False):
                    hello: str

                graph_api = cannula.CannulaAPI[MyRootType](
                    root_value={"hello": "hi"}
                )

        scalars:
            List of custom scalars to attach to the graph schema. These all should be a
            subclass of the base :py:class:`cannula.scalars.ScalarType`.
        operations:
            Optional path to an operations document or directory containing operations.
        app_directory:
            Optional path to application templates: default `app`
        opertions_directory:
            Optional path to operations templates: defaults to `app_directory/_operations`
        logger:
            Optional logger to use for messages that cannula logs. The default will be: `cannula.api`
        level:
            Optional logging level to log as (default: DEBUG)
        kwargs:
            Any extra kwargs passed directly to Starlette application.
    """

    _schema: typing.Union[str, DocumentNode, pathlib.Path]
    _root_value: typing.Optional[RootType]
    _context: typing.Type[Context]
    _scalars: typing.List[ScalarInterface]
    _kwargs: typing.Dict[str, typing.Any]
    schema: GraphQLSchema
    operations: typing.Optional[DocumentNode]
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
        operations: typing.Optional[pathlib.Path | str] = None,
        app_directory: pathlib.Path | str = "app",
        operations_directory: typing.Optional[pathlib.Path | str] = None,
        **kwargs,
    ):
        self._context = context or Context
        self._schema = schema
        self.graph_middleware = middleware
        self._root_value = root_value
        self._scalars = scalars
        self._kwargs = kwargs
        self.logger = logger
        self.level = level

        self.app_directory = pathlib.Path(app_directory)
        if operations_directory is None:
            operations_directory = self.app_directory / "_operations"
        self.operations_directory = pathlib.Path(operations_directory)

        self.schema = self._build_schema()
        self.operations = self._load_operations(operations)

        routes: typing.List[Route] = []

        # TODO(rmyers): add options here
        graphql_handler = GraphQLHandler(self)
        routes = graphql_handler.routes()

        application = AppRouter(self.app_directory)
        routes.extend(application.discover_routes())

        if self.operations is not None:
            handler = HTMXHandler(self, self.operations_directory)
            routes.append(Route("/operation/{name:str}", handler.handle_request))

        super().__init__(routes=routes, debug=True, **kwargs)

    def query(self, field_name: typing.Optional[str] = None) -> typing.Any:
        """Query Resolver

        Short cut to add a resolver for a query, by default it will use the
        name of the function as the `field_name` to be resolved::

            api = cannula.CannulaAPI(schema="type Query { something: String }")

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

            api = cannula.CannulaAPI(schema="type Mutation { make_it(name: String): String }")

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

            api = cannula.CannulaAPI(schema="type Book { name: String }")

            @api.resolver("Book")
            async def name(parent, info):
                return "hello world"

            @api.resolver("Book", field_name="something")
            async def some_other_something(parent, info):
                return "override the function name

        :param type_name: Parent object type name that is being resolved.
        :param field_name: Field name to resolve, by default the function name will be used.
        """

        def decorator(function: typing.Callable[..., typing.Any]) -> None:
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

    def _build_schema(self) -> GraphQLSchema:
        schema = build_and_extend_schema(self._find_schema(), self._scalars)

        schema_validation_errors = validate_schema(schema)
        if schema_validation_errors:
            raise SchemaValidationError(f"Invalid schema: {schema_validation_errors}")

        return schema

    def _validate_field(self, type_name: str, field_name: str) -> GraphQLField:
        object_type = self.schema.get_type(type_name)
        if object_type is None:
            raise SchemaValidationError(
                f"Invalid type '{type_name}' in resolver decorator"
            )

        # Need to cast this to object_type to satisfy mypy checks
        object_type = typing.cast(GraphQLObjectType, object_type)
        field_map = typing.cast(GraphQLFieldMap, object_type.fields)
        field_definition = field_map.get(field_name)
        if not field_definition:
            raise SchemaValidationError(
                f"Invalid field '{type_name}.{field_name}' in resolver decorator"
            )

        return field_definition

    def _load_operations(
        self, operations: pathlib.Path | str | None
    ) -> typing.Optional[DocumentNode]:
        if operations is None:
            return None

        documents = load_schema(operations)
        ops = concat_ast(documents)
        for err in validate(self.schema, ops):
            raise err
        return ops

    def get_context(self, request) -> typing.Any:
        return self._context.init(request)

    def validate(self, document: DocumentNode) -> typing.List[GraphQLError]:
        """Validate the document against the schema and store results in lru_cache."""

        @functools.lru_cache(maxsize=128)
        def _validate(document: DocumentNode) -> typing.List[GraphQLError]:
            return validate(self.schema, document)

        return _validate(document)

    def parse_document(self, document: str) -> ParseResults:
        """Parse and store the document in lru_cache."""

        @functools.lru_cache(maxsize=128)
        def _parse_document(document: str) -> ParseResults:
            try:
                document_ast = parse(document)
                return ParseResults(document_ast, [])
            except GraphQLError as err:
                return ParseResults(DocumentNode(), [err])

        return _parse_document(document)

    async def call(
        self,
        document: typing.Union[DocumentNode, str],
        *,
        variables: typing.Optional[typing.Dict[str, typing.Any]] = None,
        operation_name: typing.Optional[str] = None,
        context: typing.Optional[typing.Any] = None,
        request: typing.Optional[typing.Any] = None,
        **kwargs: typing.Any,
    ) -> ExecutionResult:
        """Preform a query against the schema.

        This is meant to be called in an asyncio.loop, if you are using a
        web framework that is synchronous use the `call_sync` method.

        :param document:
            The query or mutation to execute.
        :param variables:
            Dictionary of variable values.
        :param operation_name:
            The named operation this can be used to cache queries.
        :param context:
            The context instance to use for this operation.
        :param request:
            The original request instance for the query, this is used when
            no context is passed. By default it will be set on the info object:
            `info.context.request`
        """
        if isinstance(document, str):
            document, errors = self.parse_document(document)
            if errors:
                return ExecutionResult(data=None, errors=errors)

        if validation_errors := self.validate(document):
            return ExecutionResult(data=None, errors=validation_errors)

        if context is None:
            context = self.get_context(request)

        result = execute(
            schema=self.schema,
            document=document,
            context_value=context,
            variable_values=variables,
            operation_name=operation_name,
            middleware=self.graph_middleware,
            root_value=self._root_value,
            **kwargs,
        )
        if inspect.isawaitable(result):
            return await result
        return typing.cast(ExecutionResult, result)

    async def subscribe(
        self,
        document: typing.Union[DocumentNode, str],
        *,
        variables: typing.Optional[typing.Dict[str, typing.Any]] = None,
        operation_name: typing.Optional[str] = None,
        context: typing.Optional[typing.Any] = None,
        request: typing.Optional[typing.Any] = None,
        **kwargs: typing.Any,
    ) -> typing.AsyncIterable[ExecutionResult] | ExecutionResult:
        """Preform a query against the schema.

        This is meant to be called in an asyncio.loop, if you are using a
        web framework that is synchronous use the `call_sync` method.

        :param document:
            The query or mutation to execute.
        :param variables:
            Dictionary of variable values.
        :param operation_name:
            The named operation this can be used to cache queries.
        :param context:
            The context instance to use for this operation.
        :param request:
            The original request instance for the query, this is used when
            no context is passed. By default it will be set on the info object:
            `info.context.request`
        """
        if isinstance(document, str):
            document, errors = self.parse_document(document)
            if errors:
                return ExecutionResult(data=None, errors=errors)

        if validation_errors := self.validate(document):
            return ExecutionResult(data=None, errors=validation_errors)

        if context is None:
            context = self.get_context(request)

        return await subscribe(
            schema=self.schema,
            document=document,
            context_value=context,
            variable_values=variables,
            operation_name=operation_name,
            root_value=self._root_value,
            **kwargs,
        )

    def call_sync(
        self,
        document: typing.Union[DocumentNode, str],
        *,
        variables: typing.Optional[typing.Dict[str, typing.Any]] = None,
        operation_name: typing.Optional[str] = None,
        context: typing.Optional[typing.Any] = None,
        request: typing.Optional[typing.Any] = None,
        **kwargs: typing.Any,
    ) -> ExecutionResult:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(
            self.call(
                document=document,
                variables=variables,
                operation_name=operation_name,
                context=context,
                request=request,
                **kwargs,
            )
        )

    async def exec_operation(
        self,
        operation_name: str,
        variables: typing.Optional[typing.Dict[str, typing.Any]] = None,
        context: typing.Optional[typing.Any] = None,
        request: typing.Optional[typing.Any] = None,
        **kwargs: typing.Any,
    ) -> ExecutionResult:
        document = self.operations or ""
        return await self.call(
            document=document,
            variables=variables,
            operation_name=operation_name,
            context=context,
            request=request,
            **kwargs,
        )
