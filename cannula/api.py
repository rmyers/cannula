"""
Using the API
=============


"""

import asyncio
import collections
import copy
import functools
import logging
import inspect
import pathlib
import typing

from graphql import (
    DocumentNode,
    GraphQLError,
    GraphQLObjectType,
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
    fix_abstract_resolve_type,
    load_schema,
    maybe_parse,
)

LOG = logging.getLogger(__name__)


class ParseResults(typing.NamedTuple):
    document_ast: DocumentNode
    errors: typing.List[GraphQLError] = []


class Resolver:
    """
    Resolver Registry
    -----------------

    This class is a helper to organize your project as it grows. It allows you
    to put your resolver modules and schema in different packages. For example::

        app/
            api.py     # `api = cannula.API(args)`
        resolvers/
            books.py   # `books = cannula.Resolver(args)`
            movies.py  # `movies = cannula.Resolver(args)`


    You then register resolvers and dataloaders in the same way:

    resolvers/books.py::

        import cannula

        books = cannula.Resolver()

        @books.resolver('Query', 'books')
        def get_books(source, info, args):
            return 'Hello'

    resolvers/moives.py::

        import cannula

        movies = cannula.Resolver()

        @movies.resolver('Query', 'movies')
        def get_movies(source, info, args):
            return 'Hello'

    app/api.py::

        import cannula

        from resolvers.books import books
        from resolvers.movies import movies

        api = cannula.API(schema=SCHEMA)
        api.include_resolver(books)
        api.include_resolver(movies)


    """

    registry: typing.Dict[str, dict]
    datasources: typing.Dict[str, typing.Any]

    def __init__(
        self,
    ):
        self.registry = collections.defaultdict(dict)
        self.datasources = {}

    def resolver(self, type_name: str, field_name: str) -> typing.Any:
        def decorator(function):
            self.registry[type_name][field_name] = function

        return decorator

    def datasource(self):
        def decorator(klass):
            self.datasources[klass.__name__] = klass

        return decorator


class API(Resolver):
    """
    :param schema: GraphQL Schema for this resolver.
    :param context: Context class to hold shared state, added to GraphQLResolveInfo object.
    :param middleware: List of middleware to enable.

    Cannula API
    -----------

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
    """

    _schema: typing.Union[str, DocumentNode, pathlib.Path]
    _resolvers: typing.List[Resolver]

    def __init__(
        self,
        schema: typing.Union[str, DocumentNode, pathlib.Path],
        context: typing.Optional[Context] = None,
        middleware: typing.List[typing.Any] = [],
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._context = context or Context
        self._resolvers = []
        self._schema = schema
        self.middleware = middleware

    def include_resolver(self, resolver: Resolver):
        self._merge_registry(resolver.registry)
        self.datasources.update(resolver.datasources)

    def _find_schema(self) -> typing.List[DocumentNode]:
        schemas: typing.List[DocumentNode] = []

        if isinstance(self._schema, pathlib.Path):
            schemas.extend(load_schema(self._schema))
        else:
            schemas.append(maybe_parse(self._schema))

        return schemas

    @property
    def schema(self) -> GraphQLSchema:
        if not hasattr(self, "_full_schema"):
            self._full_schema = self._build_schema()
        return self._full_schema

    def _build_schema(self) -> GraphQLSchema:
        schema = build_and_extend_schema(self._find_schema())

        schema_validation_errors = validate_schema(schema)
        if schema_validation_errors:
            raise Exception(f"Invalid schema: {schema_validation_errors}")

        schema = fix_abstract_resolve_type(schema)

        self._make_executable(schema)

        return schema

    def _make_executable(self, schema: GraphQLSchema):
        for type_name, fields in self.registry.items():
            object_type = schema.get_type(type_name)
            if object_type is None:
                raise Exception(f"Invalid type {type_name}")

            # Need to cast this to object_type to satisfy mypy checks
            object_type = typing.cast(GraphQLObjectType, object_type)
            for field_name, resolver_fn in fields.items():
                field_definition = object_type.fields.get(field_name)
                if not field_definition:
                    raise Exception(f"Invalid field {type_name}.{field_name}")

                field_definition.resolve = resolver_fn

    def context(self):
        def decorator(klass):
            self._context = klass

        return decorator

    def get_context(self, request):
        context = self._context.init(request)
        # Initialize the datasources with a copy of the context without
        # any of the datasource attributes set. It may work just fine but
        # if you change the order the code may stop working. So discourage
        # people from this anti-pattern.
        context_copy = copy.copy(context)
        for name, datasource in self.datasources.items():
            setattr(context, name, datasource(context_copy))
        return context

    def _merge_registry(self, registry: dict):
        for type_name, value in registry.items():
            self.registry[type_name].update(value)

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
