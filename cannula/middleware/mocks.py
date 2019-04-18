import random
import typing
import uuid

from graphql import (
    GraphQLList,
    GraphQLUnionType,
)

MockObjectTypes = typing.Union[typing.Callable, str, int, float, bool, dict]

DEFAULT_MOCKS = {
    'String': lambda: random.choice(['flippy', 'flappy', 'slippy', 'slappy']),
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
        self._mock_objects = mock_objects

    def get_mocks(self, info):
        mock_header = {}

        if (
            hasattr(info.context, 'request') and
            hasattr(info.context.request, 'headers') and
            isinstance(info.context.request.header, dict)
        ):
            mock_header = info.context.request.header.get(self.mock_object_header, {})

        mock_objects = DEFAULT_MOCKS.copy() if self.mock_all else {}
        mock_objects.update(self._mock_objects)
        mock_objects.update(mock_header)
        return mock_objects

    async def resolve(self, _next, _resource, _info, **kwargs):
        type_name = _info.parent_type.name  # schema type (Query, Mutation)
        field_name = _info.field_name  # The attribute being resolved
        return_type = _info.return_type  # The field type that is being returned.

        mock_objects = self.get_mocks(_info)

        def mock_resolve_fields(schema_type: typing.Any = None):
            # Special case for list types return a random length list of type.
            if isinstance(schema_type, GraphQLList):
                mock = mock_objects.get('__list_length', 3)
                count = mock
                if callable(mock):
                    count = mock()
                return [mock_resolve_fields(schema_type.of_type) for x in range(count)]

            if isinstance(schema_type, GraphQLUnionType):
                schema_type = random.choice(schema_type.types)

            schema_type_name = str(schema_type)
            if schema_type_name.endswith('!'):
                schema_type_name = schema_type_name[:-1]

            if schema_type_name in mock_objects.keys():
                mock = mock_objects.get(schema_type_name)
                if callable(mock):
                    return mock()
                return mock

            # If we reached this point this is a custom type that has not
            # explicitly overridden in the mock_objects. Create a dummy object of
            # type 'schema_type_name' and add `__typename__` attribute to assist
            # resolving Union and Interface types.
            return_value = type(schema_type_name, (object,), {})()
            setattr(return_value, '__typename__', schema_type_name)

            return return_value

        # TODO(rmyers): handle subscriptions.
        if type_name in ['Query', 'Mutation']:
            return mock_resolve_fields(return_type)

        # First check if we previously resolved a mock object.
        if isinstance(_resource, dict):
            field_value = _resource.get(field_name)
        else:
            field_value = getattr(_resource, field_name, None)

        if field_value is None:
            field_value = mock_resolve_fields(return_type)

        return field_value
