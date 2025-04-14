import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Generator, Optional

import pytest
from graphql import DocumentNode
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.testclient import TestClient
from pydantic import BaseModel

from cannula import CannulaAPI, ResolveInfo, gql
from cannula.handlers.operations import HTMXHandler


@pytest.fixture
def template_dir(tmp_path) -> Generator[Path, None, None]:
    """
    Creates a temporary directory with the following structure:
    templates/
    ├── TestMutation_result.html
    ├── TestMutation_form.html
    """
    # Setup Templates
    templates = tmp_path / "templates"
    templates.mkdir()

    # Create an operation template
    (templates / "TestMutation_result.html").write_text(
        """<p>Operation: {{ operation.name }}</p>"""
    )

    yield templates

    # Cleanup
    shutil.rmtree(templates)


# Test Types Setup
@dataclass(kw_only=True)
class MockData:
    __typename = "MockData"
    id: Optional[str] = None
    timestamp: Optional[str] = None
    message: Optional[str] = None


class NestedValues(BaseModel):
    candy: str


class Values(BaseModel):
    nested: NestedValues
    update_cart: bool


# Root Value Resolvers
async def get_test_data(info: ResolveInfo) -> MockData:
    return MockData(
        id="some-id",
        timestamp="2025-02-01",
        message="Hello World",
    )


root_value = {
    "testData": get_test_data,
}


@pytest.fixture
def schema() -> DocumentNode:
    return gql(
        """
        type MockData {
            id: String
            timestamp: String
            message: String
        }

        type Query {
            testData: MockData
        }

        input NestedValues {
            candy: String!
        }

        input Values {
            nested: NestedValues
            update_cart: Boolean
        }

        type Mutation {
            testMutation(value: Values, dry_run: Boolean = false): MockData
        }
        """
    )


@pytest.fixture
def operations() -> DocumentNode:
    return gql(
        """
        mutation TestMutation($value: Values, $dry_run: Boolean) {
            testMutation(value: $value, dry_run: $dry_run) {
                id
            }
        }
        """
    )


@pytest.fixture
def graph(schema: DocumentNode, operations: DocumentNode) -> CannulaAPI:
    return CannulaAPI(
        root_value=root_value,
        schema=schema,
        operations=operations,
    )


@pytest.fixture
def handler(graph: CannulaAPI, template_dir) -> HTMXHandler:
    return HTMXHandler(graph, template_dir=template_dir)


@pytest.fixture
def app(handler: HTMXHandler) -> Starlette:
    app = Starlette()
    app.routes.append(Route("/operation/{name:str}", handler.handle_request))
    app.routes.append(
        Route("/operation/{name:str}", handler.handle_mutation, methods=["POST"])
    )
    return app


@pytest.fixture
def asgi_client(app: Starlette) -> TestClient:
    return TestClient(app)


async def test_mutation_operation(graph, asgi_client):
    @graph.mutation("testMutation")
    async def test_mutation(root, info, value: Values, dry_run: bool):
        assert dry_run is True
        assert value == {"nested": {"candy": "snickers"}, "update_cart": True}

    response = asgi_client.post(
        "/operation/TestMutation",
        data={
            "value.nested.candy": "snickers",
            "value.update_cart": "on",
            "dry_run": "true",
        },
        headers={"Accept": "application/json"},
    )
    assert response.status_code == 200, response.text


async def test_mutation_operation_errors(asgi_client):
    response = asgi_client.post(
        "/operation/TestMutation",
        data={
            "value.update_cart": "snickers",
            "dry_run": "true",
        },
        headers={"Accept": "application/json"},
    )
    assert response.status_code == 400, response.text
    resp = response.json()
    assert resp["data"] is None
    assert len(resp["errors"]) == 1


@pytest.mark.parametrize("operations", [None])
async def test_missing_operations(asgi_client):
    response = asgi_client.post(
        "/operation/TestMutation",
        data={"value.update_cart": "snickers", "dry_run": "true"},
    )
    assert response.status_code == 404, response.text


async def test_mutation_operation_notfound(asgi_client):
    response = asgi_client.post(
        "/operation/NotFound",
        data={"value.nested.candy": "snickers"},
        headers={"Accept": "application/json"},
    )
    assert response.status_code == 404, response.text
    assert response.text == "Mutation 'NotFound' not found"
