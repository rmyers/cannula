import pytest
from pytest_mock import MockerFixture

from cannula import API
from cannula.scalars import date


async def test_api_valid_schema_and_query(valid_schema, valid_query):
    api = API(valid_schema)
    results = await api.call(valid_query)
    assert results.errors is None


async def test_api_valid_schema_and_invalid_query(valid_schema, mocker: MockerFixture):
    api = API(valid_schema)
    results = await api.call("query Me { notFound { name } }")
    assert results.errors is not None
    assert len(results.errors) == 1
    assert results.errors[0].message == "Cannot query field 'notFound' on type 'Query'."


async def test_api_valid_schema_and_bad_query(valid_schema, mocker: MockerFixture):
    api = API(valid_schema)
    results = await api.call("query Me { ")
    assert results.errors is not None
    assert len(results.errors) == 1
    assert results.errors[0].message == "Syntax Error: Expected Name, found <EOF>."


async def test_api_scalars_missing(valid_schema):
    with pytest.raises(
        Exception, match="Invalid scalar type Date did you forget to define it?"
    ):
        API(valid_schema, scalars=[date.Date])


async def test_api_with_invalid_schema():
    with pytest.raises(
        Exception,
        match="Syntax Error: Expected Name, found <EOF>.\n\nGraphQL request:1:11\n1 | type Foo {",
    ):
        API("type Foo {")


async def test_api_with_invalid_schema_extention():
    with pytest.raises(
        Exception,
        match="Cannot extend type 'Foo' because it is not defined.",
    ):
        API("extend type Foo {name: String}")


async def test_api_with_invalid_schema_type():
    with pytest.raises(
        Exception,
        match="Unknown type 'Bar'.",
    ):
        API(
            "type Foo {name: Bar}",
        )


async def test_api_invalid_type_resolver(valid_schema):
    api = API(valid_schema)
    with pytest.raises(Exception, match="Invalid type 'Book' in resolver decorator"):

        @api.resolver("Book", "name")
        def anything(*args, **kwargs):
            pass


async def test_api_mutation(valid_schema):
    api = API(valid_schema)

    @api.mutation("createMe")
    async def createMe(*args, **kwargs):
        pass


async def test_api_invalid_field_resolver(valid_schema):
    api = API(valid_schema)
    with pytest.raises(
        Exception, match="Invalid field 'User.not_found' in resolver decorator"
    ):

        @api.resolver("User", "not_found")
        def anything(*args, **kwargs):
            pass


def test_call_sync(valid_query, valid_schema):
    api = API(valid_schema)
    results = api.call_sync(valid_query)
    assert results.errors is None
