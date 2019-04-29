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
import os
import typing

from graphql import (
    DocumentNode,
    execute,
    ExecutionResult,
    GraphQLSchema,
    parse,
    validate_schema,
    validate,
)

from .context import Context
from .helpers import get_root_path
from .schema import (
    build_and_extend_schema,
    fix_abstract_resolve_type,
    load_schema,
    maybe_parse,
)

LOG = logging.getLogger(__name__)


class Resolver:
    """Resolver Registry

    This class is a helper to organize your project as it grows. It allows you
    to put your resolver modules and schema in different packages. For example::

        app/
            api.py  # `api = cannula.API(__name__)`
        resolvers/
            subpackage/
                app.py  # `app = cannula.Resolver(__name__)`
                schema/
                   myschema.graphql

    You then register resolvers and dataloaders in the same way::

        app.py:
        import cannula

        app = cannula.Resolver(__name__)

        @app.resolver('Query')
        def my_query(source, info):
            return 'Hello'

        api.py:
        import cannula

        from resolvers.subpackage.app import app

        api = cannula.API(__name__)
        api.register_resolver(app)

    :param name: The import name of the resolver, typically `__name__`
    :param schema: GraphQL Schema for this resolver.
    :param schema_directory: Directory name to search for schema files.
    :param query_directory: Directory name to search for query docs.
    """
    # Allow sub-resolvers to apply a base schema before applying custom schema.
    base_schema: typing.Dict[str, DocumentNode] = {}
    registry: typing.Dict[str, dict]
    datasources: typing.Dict[str, typing.Any]
    forms: typing.Dict[str, typing.Any]

    def __init__(
        self,
        name: str,
        schema: typing.Optional[typing.Union[str, DocumentNode]] = None,
        schema_directory: str = 'schema',
        query_directory: str = 'queries',
    ):
        self.registry = collections.defaultdict(dict)
        self.datasources = {}
        self.forms = {}
        self._schema_directory = schema_directory
        self._query_directory = query_directory
        self.root_dir = get_root_path(name)
        self._schema = schema

    @property
    def schema_directory(self):
        if not hasattr(self, '_schema_dir'):
            if os.path.isabs(self._schema_directory):
                setattr(self, '_schema_dir', self._schema_directory)
            setattr(self, '_schema_dir', os.path.join(self.root_dir, self._schema_directory))
        return self._schema_dir

    def find_schema(self) -> typing.List[DocumentNode]:
        schemas: typing.List[DocumentNode] = []
        if os.path.isdir(self.schema_directory):
            LOG.debug(f'Searching {self.schema_directory} for schema.')
            schemas = load_schema(self.schema_directory)

        if self._schema is not None:
            schemas.append(maybe_parse(self._schema))

        return schemas

    @property
    def query_directory(self) -> str:
        if not hasattr(self, '_query_dir'):
            if os.path.isabs(self._query_directory):
                self._query_dir: str = self._query_directory
            self._query_dir = os.path.join(self.root_dir, self._query_directory)
        return self._query_dir

    @functools.lru_cache(maxsize=128)
    def load_query(self, query_name: str) -> DocumentNode:
        path = os.path.join(self.query_directory, f'{query_name}.graphql')
        assert os.path.isfile(path), f"No query found for {query_name}"

        with open(path) as query:
            return parse(query.read())

    def resolver(self, type_name: str = 'Query') -> typing.Any:
        def decorator(function):
            self.registry[type_name][function.__name__] = function
        return decorator

    def datasource(self):
        def decorator(klass):
            self.datasources[klass.__name__] = klass
        return decorator

    def get_form_query(self, name: str, **kwargs) -> DocumentNode:
        """Get registered form query document"""
        form = self.forms.get(name)
        assert form is not None, f'Form: {name} is not registered!'

        return form.get_query(**kwargs)

    def get_form_mutation(self, name: str, **kwargs) -> DocumentNode:
        """Get registered form mutation document"""
        form = self.forms.get(name)
        assert form is not None, f'Form: {name} is not registered!'

        return form.get_mutation(**kwargs)


class API(Resolver):
    """Cannula API

    Your entry point into the fun filled world of graphql. Just dive right in::

        import cannula

        api = cannula.API(__name__, schema='''
            extend type Query {
                hello(who: String): String
            }
        ''')

        @api.resolver('Query')
        def hello(who):
            return f'Hello {who}!'
    """

    def __init__(
        self,
        *args,
        resolvers: typing.List[Resolver] = [],
        context: typing.Any = Context,
        middleware: typing.List[typing.Any] = [],
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self._context = context
        self._resolvers = resolvers
        self.middleware = middleware

    @property
    def schema(self) -> GraphQLSchema:
        if not hasattr(self, '_full_schema'):
            self._full_schema = self._build_schema()
        return self._full_schema

    def _all_schema(self) -> typing.Iterator[DocumentNode]:
        for document_node in self.find_schema():
            yield document_node

        for resolver in self._resolvers:
            self._merge_registry(resolver.registry)
            self.base_schema.update(resolver.base_schema)
            self.datasources.update(resolver.datasources)
            self.forms.update(resolver.forms)
            for document_node in resolver.find_schema():
                yield document_node

        for document_node in self.base_schema.values():
            yield document_node

    def _build_schema(self) -> GraphQLSchema:
        schema = build_and_extend_schema(self._all_schema())

        schema_validation_errors = validate_schema(schema)
        if schema_validation_errors:
            raise Exception(f'Invalid schema: {schema_validation_errors}')

        schema = fix_abstract_resolve_type(schema)

        self._make_executable(schema)

        return schema

    def _make_executable(self, schema: GraphQLSchema):
        for type_name, fields in self.registry.items():
            object_type = schema.get_type(type_name)
            for field_name, resolver_fn in fields.items():
                field_definition = object_type.fields.get(field_name)
                if not field_definition:
                    raise Exception(f'Invalid field {type_name}.{field_name}')

                field_definition.resolve = resolver_fn

    def context(self):
        def decorator(klass):
            self._context = klass
        return decorator

    def get_context(self, request):
        context = self._context(request)
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

    async def call(
        self,
        document: GraphQLSchema,
        request: typing.Any = None,
        variables: typing.Dict[str, typing.Any] = None
    ) -> ExecutionResult:
        """Preform a query against the schema.

        This is meant to be called in an asyncio.loop, if you are using a
        web framework that is synchronous use the `call_sync` method.
        """
        validation_errors = validate(self.schema, document)
        if validation_errors:
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
        return result

    def call_sync(
        self,
        document: GraphQLSchema,
        request: typing.Any = None,
        variables: typing.Dict[str, typing.Any] = None
    ) -> ExecutionResult:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.call(document, request, variables))
