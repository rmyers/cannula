"""
.. _mock-middleware:

MockMiddleware
==============

Wrapps an existing schema and resolvers to provide an easy way to automatically
mock the responses from Queries, Mutations or Subscriptions. You can choose
to mock all resolvers or you could selectively provide mock objects to replace
only a handful of calls while preserving the existing resolvers.

This is really useful for end to end testing, as you can simply add a header
to the request with the mock objects you wish to replace. This way the entire
stack is validated down to the resolver level.

Example Usage
-------------

You can add the middleware in a couple different ways. If you are using the
cannula API you can add this in the middleware list in the contructor::

    import cannula
    from cannula.middleware import MockMiddleware

    api = cannula.API(
        __name__,
        SCHEMA,
        middleware = [
            MockMiddleware(
                mock_all=True,
                mock_objects={
                    'Query': {
                        'field_to_fake': 'mock_value'
                    },
                    'String': 'I will be used for any String type',
                }
            ),
        ]
    )

Or you can use this with just the `graphql-core-next` library like::

    from cannula.middleware import MockMiddleware
    from graphql import graphql

    graphql(
        schema=SCHEMA,
        query=QUERY,
        middleware=[
            MockMiddleware(
                mock_all=True,
                mock_objects={
                    'String': 'just like before'
                }
            ),
        ],
    )

Example Using `X-Mock-Objects` Header
-------------------------------------

Most testing frameworks have a way to add headers to requests that you are
testing. Usually this done for authentication, but we are going to abuse this
functionality to tell the server what data to respond with. Here is an
example using Cypress.io:

.. code-block:: javascript

    var resourceMock = JSON.stringify({
        "Resource": {
            "name": "Mocky",
            "id": "12345"
        }
    });

    describe('Test Resource View', function() {
        it('Renders the resource correctly', function() {
            cy.server({
                onAnyRequest: function(route, proxy) {
                    proxy.xhr.setRequestHeader(
                        'X-Mock-Objects', resourceMock
                    );
                }
            });
            cy.visit('http://localhost:8000/resource/view/');
            cy.get('.resource').within(() => {
                cy.get('.name').should('equal', 'Mocky');
                cy.get('.id').should('equal', '12345');
            });
        })
    });

The key difference here from mocking the request is that we are actually
making the request to the server at localhost and we know that the routes are
setup correctly. We can freely change the payload and the urls that the actual
code uses and this test will continue to function. That is, unless we break
the contract of this page and those routes no longer respond with the data
we are testing for. Since we are not actually mocking the request or the
response breaking changes will be realized by this test.

Another reason why this pattern is great is that we are not testing against
a mock server that is specifically setup to respond to our request. While that
will work just fine the mocks are hidden from the tests in some other file.
Changing that file is complicated especially if it is used in multiple tests.

Mock Middleware API
-------------------
"""

import inspect
import json
import logging
import random
import typing
import uuid

from graphql import (
    GraphQLList,
    GraphQLType,
    get_named_type,
)

MockObjectTypes = typing.Union[typing.Callable, str, int, float, bool, dict, list]

LOG = logging.getLogger(__name__)

ADJECTIVES: typing.List[str] = [
    'imminent',
    'perfect',
    'organic',
    'elderly',
    'dapper',
    'reminiscent',
    'mysterious',
    'trashy',
    'workable',
    'flaky',
    'offbeat',
    'spooky',
    'thirsty',
    'stereotyped',
    'wild',
    'devilish',
    'quarrelsome',
    'dysfunctional',
]
NOUNS: typing.List[str] = [
    'note',
    'yak',
    'hammer',
    'cause',
    'price',
    'quill',
    'truck',
    'glass',
    'color',
    'ring',
    'trees',
    'window',
    'letter',
    'seed',
    'sponge',
    'pie',
    'mass',
    'table',
    'plantation',
    'battle',
]

LIST_LENGTH_KEY: str = '__list_length'
DEFAULT_MOCKS: typing.Dict[str, MockObjectTypes] = {
    'String': lambda: f'{random.choice(ADJECTIVES)}-{random.choice(NOUNS)}',
    'Int': lambda: random.randint(4, 999),
    'Float': lambda: random.randint(5, 999) * random.random(),
    'Boolean': lambda: random.choice([True, False]),
    'ID': lambda: str(uuid.uuid4()),
    # The default number of mock items to return when results are a list.
    LIST_LENGTH_KEY: lambda: random.randint(3, 6),
}


class SuperDict(dict):
    """Wraps a dictionary to provide attribute access.

    This is returned instead of a plain `dict` object to handle cases where
    the underlining resolvers where expecting an object returned. Since we
    allow setting up mocks via a JSON header this makes it possible to
    mock only the responses while preserving the rest of the resolvers attached
    to the schema.

        >>> mock = SuperDict({'foo': {'bar': {'baz': 42}}})
        >>> print(f"{mock.foo.bar.baz} == {mock['foo']['bar']['baz']}")
        42 == 42
    """

    def __init__(self, mapping: dict):
        super().__init__([], **mapping)
        for key, value in mapping.items():
            if isinstance(value, dict):
                value = SuperDict(value)
            setattr(self, key, value)


class MockObjectStore:
    """Stores and processes the mock objects to return correct results.

    The mock objects can be various types and instead of just returning
    the raw mock we first want to convert it to a better format. IE if the
    mock is callable we want to call it first and if the results or the
    mock are a dict, we need to wrap that in our SuperDict object.
    """
    __slots__ = ['mock_objects']

    def __init__(self, mock_objects: typing.Dict[str, MockObjectTypes]):
        self.mock_objects = mock_objects

    def __contains__(self, key):
        return key in self.mock_objects

    def has_named_type(self, named_type_name: str) -> bool:
        return named_type_name in self.mock_objects

    def has_parent_field(self, parent_type_name: str, field_name: str) -> bool:
        return (
            parent_type_name in self.mock_objects and
            isinstance(self.mock_objects[parent_type_name], dict) and
            field_name in typing.cast(typing.Dict, self.mock_objects[parent_type_name])
        )

    def get(
        self,
        key: str,
        default: typing.Optional[typing.Any] = None
    ) -> typing.Any:
        mock = self.mock_objects.get(key, default)
        if mock is None:
            return

        return self.return_results(mock)

    def get_parent_field(self, parent_type_name: str, field_name: str) -> typing.Any:
        parent = self.mock_objects.get(parent_type_name)

        mock = (
            parent.get(field_name)
            if isinstance(parent, dict)
            else getattr(parent, field_name, None)
        )

        if mock is None:
            return

        return self.return_results(mock)

    def return_results(self, mock: MockObjectTypes) -> typing.Any:
        results = (
            mock()
            if callable(mock)
            else mock
        )

        if isinstance(results, list):
            return [self.maybe_wrap(r) for r in results]

        return self.maybe_wrap(results)

    def maybe_wrap(self, results: typing.Any) -> typing.Any:
        if isinstance(results, dict):
            return SuperDict(results)
        return results


class MockMiddleware:
    """Mocking Middleware

    Initialize the MockMiddleware, you can choose to mock all types or just
    the ones provided by the `mock_objects` param. Alternatively you can
    provide the mock_objects via a request header.

    :param mock_objects: Mapping of return values for types.
    :param mock_all: Whether to mock all resolvers.
    :param mock_object_header: Customize the header used to set mock_objects.
    """

    def __init__(
        self,
        mock_objects: typing.Dict[str, MockObjectTypes] = {},
        mock_all: bool = True,
        mock_object_header: str = 'X-Mock-Objects',
    ):
        self.mock_all = mock_all
        self.mock_object_header = mock_object_header
        self._mock_objects = DEFAULT_MOCKS.copy() if mock_all else {}
        self._mock_objects.update(mock_objects)

    def get_mocks(
        self,
        extra: typing.Dict[str, MockObjectTypes]
    ) -> typing.Optional[MockObjectStore]:
        mock_objects = self._mock_objects.copy()
        mock_objects.update(extra)

        if not mock_objects:
            return None

        return MockObjectStore(mock_objects)

    def get_mocks_from_headers(self, context: typing.Any) -> dict:
        try:
            mock_header = context.request.headers.get(self.mock_object_header)
            if not mock_header:
                return {}
        except Exception:
            return {}

        try:
            return json.loads(mock_header)
        except Exception:
            return {}

    async def run_next(self, _next, _resource, _info, **kwargs):
        if inspect.isawaitable(_next):
            results = await _next(_resource, _info, **kwargs)
        else:
            results = _next(_resource, _info, **kwargs)

        if inspect.isawaitable(results):
            return await results
        return results

    async def resolve(self, _next, _resource, _info, **kwargs):
        mock_header = self.get_mocks_from_headers(_info.context)
        mock_objects = self.get_mocks(extra=mock_header)
        if not mock_objects:
            return await self.run_next(_next, _resource, _info, **kwargs)

        field_name = _info.field_name
        return_type = _info.return_type
        named_type = get_named_type(return_type)
        parent_type_name = _info.parent_type.name

        resolver_is_mocked = (
            self.mock_all or
            mock_objects.has_named_type(named_type.name) or
            mock_objects.has_parent_field(parent_type_name, field_name)
        )

        if not resolver_is_mocked:
            return await self.run_next(_next, _resource, _info, **kwargs)

        if mock_objects.has_parent_field(parent_type_name, field_name):
            return mock_objects.get_parent_field(parent_type_name, field_name)

        # Check if we previously resolved a mock object.
        field_value = (
            _resource.get(field_name)
            if isinstance(_resource, dict)
            else getattr(_resource, field_name, None)
        )

        if field_value:
            return field_value

        # Finally check the return_type for mocks

        def resolve_return_type(schema_type: GraphQLType):
            # Special case for list types return a random length list of type.
            if isinstance(schema_type, GraphQLList):
                list_length = mock_objects.get(LIST_LENGTH_KEY, 3)
                return [resolve_return_type(schema_type.of_type) for x in range(list_length)]

            named_type_name = get_named_type(schema_type).name
            if named_type_name in mock_objects:
                return mock_objects.get(named_type_name)

            # If we reached this point this is a custom type that has not
            # explicitly overridden in the mock_objects. Just return a dict
            # with a `__typename` set to the type name to assist in resolving
            # Unions and Interfaces.
            return SuperDict({'__typename': named_type_name})

        return resolve_return_type(return_type)
