
import asyncio
import collections
import copy
import logging
import inspect
import os
import random
import typing
import uuid

from graphql import (
    build_schema,
    execute,
    ExecutionResult,
    extend_schema,
    parse,
    GraphQLSchema,
    validate_schema,
    validate,
)

from cannula.helpers import get_root_path
from cannula.context import Context

LOG = logging.getLogger(__name__)

# This is the root query that we provide, since the Query type cannot be
# completely empty we need to provide something that we can extend with
# the schema you are extending. We also define cacheControl directive for
# overriding field or objects cache policy.
ROOT_QUERY = """
  type Query {
    _empty: String
  }
  type Mutation {
    _empty: String
  }
  enum CacheControlScope {
    PUBLIC
    PRIVATE
  }
  directive @cacheControl(
    maxAge: Int
    scope: CacheControlScope
  ) on FIELD_DEFINITION | OBJECT | INTERFACE
"""

# TODO(rmyers): Find a better place for this.
DEFAULT_MOCKS = {
    'String': lambda: random.choice(['flippy', 'flappy', 'slippy', 'slappy']),
    'Int': lambda: random.randint(4, 999),
    'Float': lambda: random.randint(5, 999) * random.random(),
    'Boolean': lambda: random.choice([True, False]),
    'ID': lambda: str(uuid.uuid4()),
    # The default number of mock items to return when results are a list.
    '__list_length': lambda: random.randint(3, 6),
}


class Resolver:
    """Resolver Registry

    This class is a helper to organize your project as it grows. It allows you
    to put your resolver modules and schema in different packages. For example:

        app/
            api.py  # `api = cannula.API(__name__)`
        resolvers/
            subpackage/
                app.py  # `app = cannula.Resolver(__name__)`
                graphql/
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
    """

    def __init__(
        self,
        name: str,
        graphql_dir: str = 'graphql',
        schema: str = None,
    )-> typing.Any:
        self.registry = collections.defaultdict(dict)
        self.datasources = {}
        self.graphql_dir = graphql_dir
        self.root_dir = get_root_path(name)
        self._schema = schema

    def find_graphql_schema(self)-> [str]:
        _graphql_dir = self.graphql_dir
        if not os.path.isabs(_graphql_dir):
            _graphql_dir = os.path.join(self.root_dir, self.graphql_dir)

        schemas = []
        LOG.debug(f'Searching {_graphql_dir} for schema.')
        if os.path.isdir(_graphql_dir):
            files = os.listdir(_graphql_dir)
            files.sort()
            for listing in files:
                LOG.debug(f'Loading graphql file: {listing}')
                with open(os.path.join(_graphql_dir, listing)) as graph:
                    schemas.append(graph.read())

        # Finally add in any schema that was added in the constructor.
        if self._schema is not None:
            schemas.append(self._schema)

        return schemas

    def resolver(self, type_name: str = 'Query')-> typing.Any:
        def decorator(function):
            self.registry[type_name][function.__name__] = function
        return decorator

    def datasource(self):
        def decorator(klass):
            self.datasources[klass.__name__] = klass
        return decorator


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
        context: Context = Context,
        mocks: bool = False,
        mock_objects: typing.Dict = {},
        **kwargs,
    )-> typing.Any:
        super().__init__(*args, **kwargs)
        self._context = context
        self._mocks = mocks
        self._mock_objects = DEFAULT_MOCKS
        self._mock_objects.update(mock_objects)
        self._subresolvers = []
        self._graphql_schema = self.find_graphql_schema()

    @property
    def schema(self):
        if not hasattr(self, '_full_schema'):
            self._full_schema = self._build_schema()
        return self._full_schema

    def _build_schema(self) -> GraphQLSchema:
        schema = build_schema(ROOT_QUERY)

        for extention in self._graphql_schema:
            schema = extend_schema(schema, parse(extention))

        schema_validation_errors = validate_schema(schema)
        if schema_validation_errors:
            raise Exception(f'Invalid schema: {schema_validation_errors}')

        return schema

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

    def register_resolver(self, resolver: Resolver) -> None:
        """Register a sub-resolver.

        This will add in all the datasources/resolvers/schema from the
        sub-resolver.
        """
        self._graphql_schema += resolver.find_graphql_schema()
        self._merge_registry(resolver.registry)
        self.datasources.update(resolver.datasources)

    async def call(
        self,
        document: GraphQLSchema,
        request: typing.Any = None,
        variables: typing.Dict[str, typing.Any] = None
    )-> ExecutionResult:
        """Preform a query against the schema.

        This is meant to be called in an asyncio.loop, if you are using a
        web framework that is synchronous use the `call_sync` method.
        """
        field_resolver = self.field_resolver
        if self._mocks:
            field_resolver = self.mock_resolver

        validation_errors = validate(self.schema, document)
        if validation_errors:
            return ExecutionResult(data=None, errors=validation_errors)

        context = self.get_context(request)
        result = execute(
            schema=self.schema,
            document=document,
            context_value=context,
            variable_values=variables,
            field_resolver=field_resolver
        )
        if inspect.isawaitable(result):
            return await result
        return result

    def call_sync(
        self,
        document: GraphQLSchema,
        request: typing.Any = None,
        variables: typing.Dict[str, typing.Any] = None
    )-> ExecutionResult:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.call(document, request, variables))

    async def mock_resolver(self, resource, info, **kwargs):
        from graphql.type.definition import GraphQLList

        def resolve_fields(schema_type):
            """Recursively resolve the schema_type.

            If there is a mock object defined for this type return it otherwise
            loop over all the fields and build an object with mock data.
            """

            # Special case for list types return a random length list of type.
            if isinstance(schema_type, GraphQLList):
                mock = self._mock_objects.get('__list_length')
                count = mock
                if callable(mock):
                    count = mock()
                return [resolve_fields(schema_type.of_type) for x in range(count)]

            schema_type = str(schema_type)
            if schema_type.endswith('!'):
                schema_type = schema_type[:-1]

            if schema_type in self._mock_objects.keys():
                mock = self._mock_objects.get(schema_type)
                if callable(mock):
                    return mock()
                return mock

            return_value = type(schema_type, (object,), {})()

            found = info.schema.get_type(schema_type)
            for name, field in found.fields.items():
                setattr(return_value, name, resolve_fields(field.type))

            return return_value

        return resolve_fields(info.return_type)

    async def field_resolver(self, _resource, _info, **kwargs):
        type_name = _info.parent_type.name  # schema type (Query, Mutation)
        field_name = _info.field_name  # The attribute being resolved
        try:
            # First check if there is a customer resolver in the registry
            custom_resolver = self.registry[type_name][field_name]
            return await custom_resolver(_resource, _info, **kwargs)
        except KeyError:
            # If there is not a custom resolver check the resource for attributes
            # that match the field_name. The resource argument will be the result
            # of the Query type resolution.
            return getattr(_resource, field_name, None)
