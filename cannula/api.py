
import asyncio
import collections
import copy
import logging
import inspect
import os
import typing

from graphql import (
    default_field_resolver,
    DocumentNode,
    execute,
    ExecutionResult,
    GraphQLSchema,
    GraphQLUnionType,
    validate_schema,
    validate,
)

from .context import Context
from .helpers import get_root_path
from .schema import build_and_extend_schema, load_schema, maybe_parse

LOG = logging.getLogger(__name__)


class Resolver:
    """Resolver Registry

    This class is a helper to organize your project as it grows. It allows you
    to put your resolver modules and schema in different packages. For example:

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
    """
    # Allow sub-resolvers to apply a base schema before applying custom schema.
    base_schema: typing.Dict[str, DocumentNode] = {}
    registry: typing.Dict[str, dict]
    datasources: typing.Dict[str, typing.Any]

    def __init__(
        self,
        name: str,
        graphql_directory: str = 'schema',
        schema: typing.Union[str, DocumentNode] = None,
    ):
        self.registry = collections.defaultdict(dict)
        self.datasources = {}
        self._graphql_directory = graphql_directory
        self.root_dir = get_root_path(name)
        self._schema = schema

    @property
    def graphql_directory(self):
        if not hasattr(self, '_schema_dir'):
            if os.path.isabs(self._graphql_directory):
                setattr(self, '_schema_dir', self._graphql_directory)
            setattr(self, '_schema_dir', os.path.join(self.root_dir, self._graphql_directory))
        return self._schema_dir

    def find_graphql_schema(self) -> typing.List[DocumentNode]:
        schemas: typing.List[DocumentNode] = []
        if os.path.isdir(self.graphql_directory):
            LOG.debug(f'Searching {self.graphql_directory} for schema.')
            schemas = load_schema(self.graphql_directory)

        if self._schema is not None:
            schemas.append(maybe_parse(self._schema))

        return schemas

    def resolver(self, type_name: str = 'Query') -> typing.Any:
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
        resolvers: typing.List[Resolver] = [],
        context: typing.Any = Context,
        middleware: typing.List[typing.Any] = [],
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self._context = context
        self._resolvers = resolvers
        self._middleware = middleware
        self._graphql_schema = self.find_graphql_schema()

    @property
    def schema(self) -> GraphQLSchema:
        if not hasattr(self, '_full_schema'):
            self._full_schema = self._build_schema()
            self.fix_abstract_resolve_type(self._full_schema)
        return self._full_schema

    def fix_abstract_resolve_type(self, schema: GraphQLSchema) -> None:
        # We need to provide a custom 'resolve_type' since the default
        # in method only checks for __typename if the source is a dict.
        # Python mangles the variable name if it starts with `__` so we add
        # `__typename__` attribute which is not mangled.
        # TODO(rmyers): submit PR to fix upstream?

        def custom_resolve_type(source, _info):
            if isinstance(source, dict):
                return str(source.get('__typename'))
            return getattr(source, '__typename__', None)

        for _type_name, graphql_type in schema.type_map.items():
            if isinstance(graphql_type, GraphQLUnionType):
                graphql_type.resolve_type = custom_resolve_type

    def _build_schema(self) -> GraphQLSchema:
        ast_documents = self._graphql_schema + list(self.base_schema.values())
        schema = build_and_extend_schema(ast_documents)

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
        self.base_schema.update(resolver.base_schema)
        self._graphql_schema += resolver.find_graphql_schema()
        self._merge_registry(resolver.registry)
        self.datasources.update(resolver.datasources)

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
            field_resolver=self.field_resolver,
            middleware=self._middleware,
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
            return default_field_resolver(_resource, _info, **kwargs)
