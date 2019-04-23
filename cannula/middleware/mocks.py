import inspect
import json
import random
import typing
import uuid

from graphql import (
    GraphQLList,
    GraphQLNonNull,
    GraphQLType,
    GraphQLUnionType,
    get_named_type,
)

MockObjectTypes = typing.Union[typing.Callable, str, int, float, bool, dict]

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

DEFAULT_MOCKS: typing.Dict[str, MockObjectTypes] = {
    'String': lambda: f'{random.choice(ADJECTIVES)}-{random.choice(NOUNS)}',
    'Int': lambda: random.randint(4, 999),
    'Float': lambda: random.randint(5, 999) * random.random(),
    'Boolean': lambda: random.choice([True, False]),
    'ID': lambda: str(uuid.uuid4()),
    # The default number of mock items to return when results are a list.
    '__list_length': lambda: random.randint(3, 6),
}


class MockMiddleware:

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
        ll_mock = self._mock_objects.get('__list_length', 3)
        self.list_length = ll_mock() if callable(ll_mock) else ll_mock

    def get_mocks(self, extra: dict) -> dict:
        mock_objects = self._mock_objects.copy()
        mock_objects.update(extra)
        return mock_objects

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

        return_type = _info.return_type
        if not self.mock_all:
            return_type = is_valid_return_type(mock_objects, _info.return_type)

        if not return_type:
            return await self.run_next(_next, _resource, _info, **kwargs)

        type_name = _info.parent_type.name  # schema type (Query, Mutation)
        field_name = _info.field_name  # The attribute being resolved

        def mock_resolve_fields(schema_type: typing.Any = None):
            # Special case for list types return a random length list of type.
            if isinstance(schema_type, GraphQLList):
                return [mock_resolve_fields(schema_type.of_type) for x in range(self.list_length)]

            named_type = get_named_type(return_type)

            if named_type.name in mock_objects.keys():
                mock = mock_objects.get(schema_type.name)
                return mock() if callable(mock) else mock

            # If we reached this point this is a custom type that has not
            # explicitly overridden in the mock_objects. Just return a dict
            # with a `__typename` set to the type name to assist in resolving
            # Unions and Interfaces.
            return {'__typename': named_type.name}

        if type_name in ['Query', 'Mutation', 'Subscription']:
            return mock_resolve_fields(return_type)

        # Check if we previously resolved a mock object.
        if isinstance(_resource, dict):
            field_value = _resource.get(field_name)
        else:
            field_value = getattr(_resource, field_name, None)

        if field_value is None:
            field_value = mock_resolve_fields(return_type)

        return field_value


def is_valid_return_type(
    mock_objects: dict,
    return_type: typing.Any
) -> GraphQLType:
    available_mocks = list(mock_objects.keys())

    if isinstance(return_type, GraphQLList):
        list_type = return_type.of_type
        return return_type if is_valid_return_type(mock_objects, list_type) else None

    named_type = get_named_type(return_type)

    return return_type if named_type.name in available_mocks else None
