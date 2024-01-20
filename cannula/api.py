"""
Using the API
=============


"""

import asyncio
import collections
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


class Resolver:
    """
    This class is a helper to organize your project as it grows. It allows you
    to put your resolver modules and schema in different packages. For example::

        app/
            api.py     # `api = cannula.API(args)`
        resolvers/
            books.py   # `books = cannula.Resolver()`
            movies.py  # `movies = cannula.Resolver()`


    You then register resolvers and dataloaders in the same way:

    resolvers/books.py::

        import cannula

        from database.books import get_books

        books = cannula.Resolver()

        @books.query('books')
        async def get_books(source, info, args):
            return await get_books()

    resolvers/moives.py::

        import cannula

        from database.movies import get_movies, fetch_movies_for_book

        movies = cannula.Resolver()

        @movies.query('movies')
        async def get_movies(source, info, args):
            return await get_movies()

        @movies.revolver('Books', 'movies')
        async def list_movies_for_book(book, info) -> list[Movie]:
            return await fetch_movies_for_book(book.id)

    app/api.py::

        import cannula

        from resolvers.books import books
        from resolvers.movies import movies

        api = cannula.API(schema=SCHEMA)
        api.include_resolver(books)
        api.include_resolver(movies)


    """

    registry: typing.Dict[str, dict]

    def __init__(self):
        self.registry = collections.defaultdict(dict)

    def query(self, field_name: typing.Optional[str] = None) -> typing.Any:
        """Query Resolver

        Short cut to add a resolver for a query, by default it will use the
        name of the function as the `field_name` to be resolved::

            resolver = cannula.Resolver()

            @resolver.query
            async def something(parent, info) -> str:
                return "hello world"

            @resolver.query(field_name="something")
            async def some_other_something(parent, info) -> str:
                return "override the function name"

        :param field_name: Field name to resolve, by default the function name will be used.
        """
        return self.resolver("Query", field_name)

    def mutation(self, field_name: typing.Optional[str] = None) -> typing.Any:
        """Mutation Resolver

        Short cut to add a resolver for a mutation, by default it will use the
        name of the function as the `field_name` to be resolved::

            resolver = cannula.Resolver()

            @resolver.mutation
            async def make_it(parent, info, name: str) -> str:
                return "hello world"

            @resolver.mutation(field_name="make_it")
            async def some_other_something(parent, info, name: str) -> str:
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

            resolver = cannula.Resolver()

            @resolver.resolver("Book")
            async def name(parent, info) -> str:
                return "hello world"

            @resolver.resolver("Book", field_name="something")
            async def some_other_something(parent, info):
                return "override the function name

        :param type_name: Parent object type name that is being resolved.
        :param field_name: Field name to resolve, by default the function name will be used.
        """

        def decorator(function):
            _name = field_name or function.__name__
            self.registry[type_name][_name] = function

        return decorator


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
    _resolvers: typing.List[Resolver]
    _root_value: typing.Optional[RootType]
    _kwargs: typing.Dict[str, typing.Any]

    def __init__(
        self,
        schema: typing.Union[str, DocumentNode, pathlib.Path],
        context: typing.Optional[typing.Any] = None,
        middleware: typing.List[typing.Any] = [],
        root_value: typing.Optional[RootType] = None,
        **kwargs,
    ):
        self._context = context or Context
        self._resolvers = []
        self._schema = schema
        self.middleware = middleware
        self._root_value = root_value
        self._kwargs = kwargs

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

    def include_resolver(self, resolver: Resolver):
        """Include a set of resolvers

        This is used to break up a larger application into different modules.
        For example you can group all the resolvers for a specific feature set::

            from cannula import Resolver

            from database import Book, filter_books, get_book

            book_resolver = Resolver()

            @book_resolver.query
            async def books(parent, info, **args) -> list[Book]:
                return await filter_books(**args)

            @book_resolver.query
            async def book(parent, info, book_id: str) -> Book:
                return await get_book(book_id)

        Then include the resolver in the main cannula API::

            import cannula
            import pathlib

            from features.books import book_resolver

            api = cannula.API(schema=pathlib.Path('.'))
            api.include_resolver(book_resolver)

        """
        self._merge_registry(resolver.registry)

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

        return schema

    def _validate_field(self, type_name: str, field_name: str) -> GraphQLField:
        object_type = self.schema.get_type(type_name)
        if object_type is None:
            raise Exception(f"Invalid type {type_name}")

        # Need to cast this to object_type to satisfy mypy checks
        object_type = typing.cast(GraphQLObjectType, object_type)
        field_map = typing.cast(GraphQLFieldMap, object_type.fields)
        field_definition = field_map.get(field_name)
        if not field_definition:
            raise Exception(f"Invalid field {type_name}.{field_name}")

        return field_definition

    def context(self):
        def decorator(klass):
            self._context = klass

        return decorator

    def get_context(self, request) -> typing.Any:
        return self._context.init(request)

    def _merge_registry(self, registry: dict):
        for type_name, value in registry.items():
            for field_name, revolve_fn in value.items():
                field_def = self._validate_field(type_name, field_name)
                field_def.resolve = revolve_fn

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
