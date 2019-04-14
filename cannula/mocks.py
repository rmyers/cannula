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


class MockSchemaResolver:

    def __init__(self, mock_objects: typing.Dict[str, MockObjectTypes] = {}):
        self._mock_objects = DEFAULT_MOCKS.copy()
        self._mock_objects.update(mock_objects)

    def mock_resolve_fields(self, schema_type):
        # Special case for list types return a random length list of type.
        if isinstance(schema_type, GraphQLList):
            mock = self._mock_objects.get('__list_length')
            count = mock
            if callable(mock):
                count = mock()
            return [self.mock_resolve_fields(schema_type.of_type) for x in range(count)]

        if isinstance(schema_type, GraphQLUnionType):
            schema_type = random.choice(schema_type.types)

        schema_type_name = str(schema_type)
        if schema_type_name.endswith('!'):
            schema_type_name = schema_type_name[:-1]

        if schema_type_name in self._mock_objects.keys():
            mock = self._mock_objects.get(schema_type_name)
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

    async def __call__(self, _resource, _info, **kwargs):
        type_name = _info.parent_type.name  # schema type (Query, Mutation)
        field_name = _info.field_name  # The attribute being resolved
        return_type = _info.return_type  # The field type that is being returned.

        # TODO(rmyers): Handle all other base types
        if type_name in ['Query', 'Mutation']:
            return self.mock_resolve_fields(return_type)

        # First check if we previously resolved a mock object.
        if isinstance(_resource, dict):
            field_value = _resource.get(field_name)
        else:
            field_value = getattr(_resource, field_name, None)

        if field_value is None:
            field_value = self.mock_resolve_fields(return_type)

        return field_value
