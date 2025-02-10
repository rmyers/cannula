import pytest
from graphql import ExecutionResult, GraphQLError
from pytest_mock import MockerFixture

from cannula.api import CannulaAPI, SchemaValidationError
from cannula.scalars import date


async def test_api_valid_schema_and_query(valid_schema, valid_query):
    api = CannulaAPI(valid_schema)
    results = await api.call(valid_query)
    assert results.errors is None


async def test_api_valid_schema_and_invalid_query(valid_schema, mocker: MockerFixture):
    api = CannulaAPI(valid_schema)
    results = await api.call("query Me { notFound { name } }")
    assert results.errors is not None
    assert len(results.errors) == 1
    assert results.errors[0].message == "Cannot query field 'notFound' on type 'Query'."


async def test_api_valid_schema_and_bad_query(valid_schema, mocker: MockerFixture):
    api = CannulaAPI(valid_schema)
    results = await api.call("query Me { ")
    assert results.errors is not None
    assert len(results.errors) == 1
    assert results.errors[0].message == "Syntax Error: Expected Name, found <EOF>."


async def test_api_valid_schema_and_invalid_subscription(
    valid_schema, mocker: MockerFixture
):
    api = CannulaAPI(valid_schema)
    results = await api.subscribe("subscription Me { notFound { name } }")
    assert isinstance(results, ExecutionResult)
    assert results.errors is not None
    assert len(results.errors) == 1
    assert (
        results.errors[0].message
        == "Cannot query field 'notFound' on type 'Subscription'."
    )


async def test_api_valid_schema_and_bad_subscription(
    valid_schema, mocker: MockerFixture
):
    api = CannulaAPI(valid_schema)
    results = await api.subscribe("subscription Me { ")
    assert isinstance(results, ExecutionResult)
    assert results.errors is not None
    assert len(results.errors) == 1
    assert results.errors[0].message == "Syntax Error: Expected Name, found <EOF>."


async def test_api_scalars(valid_schema):
    api = CannulaAPI(valid_schema, scalars=[date.Date])
    assert api is not None


async def test_api_with_invalid_schema():
    with pytest.raises(
        Exception,
        match="Syntax Error: Expected Name, found <EOF>.",
    ):
        CannulaAPI("type Foo {")


async def test_api_with_invalid_schema_extention():
    with pytest.raises(
        Exception,
        match="Cannot extend type 'Foo' because it is not defined.",
    ):
        CannulaAPI("extend type Foo {name: String}")


async def test_api_with_invalid_schema_type():
    with pytest.raises(
        Exception,
        match="Unknown type 'Bar'.",
    ):
        CannulaAPI(
            "type Foo {name: Bar}",
        )


async def test_api_invalid_type_resolver(valid_schema):
    api = CannulaAPI(valid_schema)
    with pytest.raises(Exception, match="Invalid type 'Book' in resolver decorator"):

        @api.resolver("Book", "name")
        def anything(*args, **kwargs):
            pass


async def test_api_mutation(valid_schema):
    api = CannulaAPI(valid_schema)

    @api.mutation("createMe")
    async def createMe(*args, **kwargs):
        pass


async def test_api_invalid_field_resolver(valid_schema):
    api = CannulaAPI(valid_schema)
    with pytest.raises(
        Exception, match="Invalid field 'User.not_found' in resolver decorator"
    ):

        @api.resolver("User", "not_found")
        def anything(*args, **kwargs):
            pass


def test_call_sync(valid_query, valid_schema):
    api = CannulaAPI(valid_schema)
    results = api.call_sync(valid_query)
    assert results.errors is None


def test_invalid_interface_implementation():
    # This schema will build but fail validation because Book implements
    # the SearchResult interface but changes the return type of the 'id' field
    invalid_schema = """
    interface SearchResult {
        id: ID!
        title: String!
    }

    type Book implements SearchResult {
        id: String!  # This is invalid - must be ID! to match interface
        title: String!
    }

    type Query {
        search: [SearchResult]
    }
    """

    with pytest.raises(SchemaValidationError) as exc_info:
        CannulaAPI(schema=invalid_schema)

    assert "Invalid schema" in str(exc_info.value)


def test_invalid_union_member():
    # This schema will build but fail validation because the union
    # includes an interface which is not allowed
    invalid_schema = """
    interface Named {
        name: String!
    }

    type Book {
        title: String!
    }

    union SearchResult = Named | Book  # Interfaces can't be union members

    type Query {
        search: [SearchResult]
    }
    """

    with pytest.raises(TypeError) as exc_info:
        CannulaAPI(schema=invalid_schema)

    assert (
        "SearchResult types must be specified as a collection of GraphQLObjectType instances."
        in str(exc_info.value)
    )


def test_invalid_field_arguments():
    # This schema will build but fail validation because the input type
    # is not defined
    invalid_schema = """
    type Query {
        search(filter: FilterInput!): String  # FilterInput is not defined
    }
    """

    with pytest.raises(TypeError) as exc_info:
        CannulaAPI(schema=invalid_schema)

    assert "Unknown type 'FilterInput'" in str(exc_info.value)


def test_invalid_operations(valid_schema, tmp_path):
    operation_file = tmp_path / "operations.graphql"
    operation_file.write_text(
        """
        query Invalid {
            does_not_exist {
                name
            }
        }
    """
    )

    with pytest.raises(GraphQLError) as exc_info:
        CannulaAPI(schema=valid_schema, operations=operation_file)

    assert "Cannot query field 'does_not_exist' on type 'Query'" in str(exc_info.value)
