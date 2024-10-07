from pytest_mock import MockerFixture

from cannula import API

VALID_SCHEMA = """\
type User { name: String }
type Query { me: User }
"""


async def test_api_valid_schema_and_query():
    api = API(VALID_SCHEMA)
    results = await api.call("query Me { me { name } }")
    assert results.errors is None


async def test_api_valid_schema_and_invalid_query(mocker: MockerFixture):
    api = API(VALID_SCHEMA)
    results = await api.call("query Me { notFound { name } }")
    assert results.errors is not None
    assert len(results.errors) == 1
    assert results.errors[0].message == "Cannot query field 'notFound' on type 'Query'."
