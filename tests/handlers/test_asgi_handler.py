import asyncio
from dataclasses import dataclass
from typing import AsyncIterator, Dict, Any, Generator, Optional
from graphql import DocumentNode
from unittest.mock import ANY

import pytest
from starlette.applications import Starlette
from starlette.testclient import TestClient, WebSocketTestSession
from cannula import CannulaAPI, ResolveInfo, gql
from cannula.handlers.asgi import GraphQLHandler, GQLMessageType


# Test Types Setup
@dataclass(kw_only=True)
class MockData:
    __typename = "MockData"
    id: Optional[str] = None
    timestamp: Optional[str] = None
    message: Optional[str] = None


# Root Value Resolvers
async def get_test_data(info: ResolveInfo) -> MockData:
    return MockData(
        id="some-id",
        timestamp="2025-02-01",
        message="Hello World",
    )


class AsyncRange:
    def __init__(self, start, end):
        self.start = start
        self.end = end

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.start > self.end:
            await asyncio.sleep(0.001)
            value = self.start
            self.start -= 1
            return value
        else:
            raise StopAsyncIteration


async def async_subscription(info: ResolveInfo) -> AsyncIterator[dict[str, MockData]]:
    async for i in AsyncRange(3, -1):
        yield {
            "testSubscription": MockData(
                id="some-id",
                timestamp="some-date",
                message=f"Update {i}",
            )
        }
        await asyncio.sleep(0.01)


async def async_subscription_error(info: ResolveInfo) -> Any:
    async for i in AsyncRange(3, -1):
        raise Exception("something went a foul")


root_value = {
    "testData": get_test_data,
    "testSubscription": async_subscription,
    "testSubscriptionError": async_subscription_error,
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

        type Subscription {
            testSubscription: MockData
            testSubscriptionError: String
        }
        """
    )


@pytest.fixture
def graph(schema):
    return CannulaAPI(
        root_value=root_value,
        schema=schema,
    )


@pytest.fixture
def app(graph):
    app = Starlette()
    handler = GraphQLHandler(graph, path="/graphql", graphiql=True)
    app.routes.extend(handler.routes())
    return app


@pytest.fixture
def asgi_client(app):
    return TestClient(app)


@pytest.fixture
def websocket(asgi_client) -> Generator[WebSocketTestSession, None, None]:
    with asgi_client.websocket_connect(
        "/graphql", subprotocols=["graphql-transport-ws"]
    ) as websocket:
        # Connection init
        websocket.send_json({"type": GQLMessageType.CONNECTION_INIT})
        response = websocket.receive_json()
        assert response["type"] == GQLMessageType.CONNECTION_ACK

        yield websocket


async def test_query_with_scalars(asgi_client):
    query = """
        query MockData {
            testData {
                id
                message
            }
        }
    """
    response = asgi_client.post("/graphql", json={"query": query})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["errors"] is None
    assert data["data"]["testData"] == {
        "id": "some-id",
        "message": "Hello World",
    }


async def test_websocket_subscription(websocket):
    # Subscribe
    subscription_id = "1"
    websocket.send_json(
        {
            "id": subscription_id,
            "type": GQLMessageType.SUBSCRIBE,
            "payload": {
                "query": """
                        subscription {
                            testSubscription {
                                id
                                message
                            }
                        }
                    """
            },
        }
    )

    # Receive messages
    async for i in AsyncRange(3, -1):
        response = websocket.receive_json()
        print(response)
        assert response["type"] == GQLMessageType.NEXT
        assert response["id"] == subscription_id
        payload = response["payload"]["data"]["testSubscription"]
        assert payload["id"] == "some-id"
        assert payload["message"] == f"Update {i}"

    # Complete message
    response = websocket.receive_json()
    assert response["type"] == GQLMessageType.COMPLETE
    assert response["id"] == subscription_id


async def test_websocket_subscription_early_cancel(websocket):
    # Subscribe
    subscription_id = "2"
    websocket.send_json(
        {
            "id": subscription_id,
            "type": GQLMessageType.SUBSCRIBE,
            "payload": {
                "query": """
                        subscription {
                            testSubscription {
                                id
                                message
                            }
                        }
                    """
            },
        }
    )

    # Receive a single message then close
    response = websocket.receive_json()
    print(response)
    assert response["type"] == GQLMessageType.NEXT
    websocket.send_json({"type": GQLMessageType.COMPLETE, "id": subscription_id})
    assert websocket.should_close


async def test_websocket_subscription_close_socket(websocket):
    # Subscribe
    subscription_id = "2"
    websocket.send_json(
        {
            "id": subscription_id,
            "type": GQLMessageType.SUBSCRIBE,
            "payload": {"query": "subscription { testSubscription { id } }"},
        }
    )
    websocket.close()
    websocket.send_json({"type": GQLMessageType.PING})
    response = websocket.receive_json()
    assert response is None


async def test_websocket_subscription_errors(websocket):
    # Subscribe
    subscription_id = "2"
    websocket.send_json(
        {
            "id": subscription_id,
            "type": GQLMessageType.SUBSCRIBE,
            "payload": {"query": "subscription { testSubscriptionError }"},
        }
    )

    # Receive a single message then close
    response = websocket.receive_json()
    print(response)
    assert response["type"] == GQLMessageType.ERROR
    assert response["payload"] == [
        {
            "locations": ANY,
            "message": "something went a foul",
            "path": [
                "testSubscriptionError",
            ],
        }
    ]


@pytest.mark.parametrize(
    "query,variables,expected_status,expected_response",
    [
        (
            """
            query MockData {
                testData {
                    id
                    message
                }
            }
            """,
            None,
            200,
            {
                "data": {"testData": {"id": "some-id", "message": "Hello World"}},
                "errors": None,
                "extensions": None,
            },
        ),
        (
            "invalid query",
            None,
            200,
            {
                "data": None,
                "errors": [
                    {
                        "locations": ANY,
                        "message": "Syntax Error: Unexpected Name 'invalid'.",
                    }
                ],
                "extensions": None,
            },
        ),
        (
            None,
            None,
            400,
            {
                "errors": [
                    {
                        "message": "No GraphQL query found in the request",
                    }
                ]
            },
        ),
    ],
)
async def test_graphql_parameterized(
    asgi_client,
    query: Optional[str],
    variables: Optional[Dict[str, Any]],
    expected_status: int,
    expected_response: Dict[str, Any],
):
    response = asgi_client.post(
        "/graphql", json={"query": query, "variables": variables}
    )
    assert response.status_code == expected_status, response.text
    data = response.json()
    assert data == expected_response


async def test_graphiql_interface(asgi_client):
    response = asgi_client.get("/graphql", headers={"accept": "text/html"})
    assert response.status_code == 200, response.text
    assert "text/html" in response.headers["content-type"]


async def test_invalid_method(asgi_client):
    response = asgi_client.put("/graphql", headers={"accept": "application/json"})
    assert response.status_code == 405, response.text
    data = response.json()
    assert data["errors"][0]["message"] == "Method not allowed"


async def test_invalid_json(asgi_client):
    response = asgi_client.post("/graphql", content="{'query': 'not-valid'}")
    assert response.status_code == 400, response.text
    data = response.json()
    assert data["errors"][0]["message"] == "Invalid JSON"


async def test_websocket_invalid_subscription(websocket):
    # Subscribe
    subscription_id = "1"
    websocket.send_json(
        {
            "id": subscription_id,
            "type": GQLMessageType.SUBSCRIBE,
            "payload": {
                "query": """
                        subscription {
                            nonExistent {
                                id
                            }
                        }
                    """
            },
        }
    )

    response = websocket.receive_json()
    print(response)
    assert response["type"] == GQLMessageType.ERROR
    assert response["id"] == subscription_id
    payload = response["payload"]
    assert payload == [
        {
            "locations": ANY,
            "message": "Cannot query field 'nonExistent' on type 'Subscription'.",
        }
    ]
