import logging
from graphql import DocumentNode
import pytest

import cannula

LOG = logging.getLogger("cannula.tests")


logging.basicConfig(
    level=logging.DEBUG, filename="reports/test-report.log", filemode="w"
)


def pytest_runtest_setup(item):
    LOG.info("=======================================================")
    LOG.info(f"Running test: {item.name}")
    LOG.info("=======================================================")


@pytest.fixture
def valid_schema() -> DocumentNode:
    return cannula.gql(
        """
        type User {
            name: String
        }
        type Query {
            me: User
            you: User
        }
        type Mutation {
            createMe(name: String!): User
        }
        """
    )


@pytest.fixture
def valid_query() -> DocumentNode:
    return cannula.gql("query Me { me { name } }")


@pytest.fixture
def valid_query_string() -> str:
    return "query Me { me { name } }"
