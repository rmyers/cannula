import pytest

from tests.conftest import GraphClient


@pytest.fixture
def graphql_path() -> str:
    return "/part1/graph"


QUERY = """
        query LoggedInUser {
            me {
                name
            }
        }
"""


async def test_part_one_graphql_endpoint(graphql_client: GraphClient, graphql_path):
    resp = await graphql_client(QUERY)
    assert resp.data is not None
    assert resp.errors is None
    assert resp.data["me"] is None
