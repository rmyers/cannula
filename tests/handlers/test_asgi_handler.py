import asyncio
from dataclasses import dataclass
from typing import AsyncIterator, Dict, Any, Generator, Optional
import uuid
from graphql import DocumentNode
from unittest.mock import ANY

import pytest
from starlette.applications import Starlette
from starlette.testclient import TestClient, WebSocketTestSession
from starlette.websockets import WebSocketDisconnect, WebSocket

from cannula import CannulaAPI, ResolveInfo, gql
from cannula.handlers.asgi import GraphQLHandler, GQLMessageType, SubscriptionManager


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
def graph(schema: DocumentNode) -> CannulaAPI:
    return CannulaAPI(
        root_value=root_value,
        schema=schema,
    )


@pytest.fixture
def handler(graph: CannulaAPI) -> GraphQLHandler:
    return GraphQLHandler(graph, path="/graphql", graphiql=True)


@pytest.fixture
def app(handler: GraphQLHandler) -> Starlette:
    app = Starlette()
    app.routes.extend(handler.routes())
    return app


@pytest.fixture
def asgi_client(app: Starlette) -> TestClient:
    return TestClient(app)


@pytest.fixture
def websocket(asgi_client: TestClient) -> Generator[WebSocketTestSession, None, None]:
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
        pytest.param(
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
            id="normal",
        ),
        pytest.param(
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
            id="invalid-query",
        ),
        pytest.param(
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
            id="no-query",
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
            "payload": {"query": "subscription { nonExistent { id } }"},
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


async def test_websocket_connection_error(handler, mocker):
    """Test handling of general connection errors during WebSocket communication"""
    # Mock WebSocket to raise an exception during send_json
    mock_websocket = mocker.MagicMock(spec=WebSocket)
    mock_websocket.send_json.side_effect = ConnectionError("Simulated connection error")

    # Call handle_websocket directly
    await handler.handle_websocket(mock_websocket)

    # Verify close was attempted
    mock_websocket.close.assert_called_once()


async def test_connection_error_during_init(app, mocker):
    """Test handling of connection error during WebSocket initialization"""
    mock_websocket = mocker.MagicMock(spec=WebSocket)

    # Mock accept to raise an error
    mock_websocket.iter_json.side_effect = ConnectionError(
        "Failed to initialize connection"
    )

    # Create handler and attempt connection
    handler = GraphQLHandler(app.routes[0].app, path="/graphql")
    try:
        await handler.handle_websocket(mock_websocket)
    except Exception:
        pass

    # Verify close was attempted
    mock_websocket.close.assert_called_once()


async def test_abnormal_close(handler, mocker):
    """Test handling of connection error during WebSocket initialization"""
    mock_websocket = mocker.MagicMock(spec=WebSocket)

    # Mock accept to raise an error
    mock_websocket.iter_json.side_effect = WebSocketDisconnect(
        code=1006, reason="blame canada"
    )

    # Create handler and attempt connection
    try:
        await handler.handle_websocket(mock_websocket)
    except Exception:
        pass

    # Verify close was attempted
    mock_websocket.close.assert_called_once()


async def test_connection_invalid_message(websocket):
    """Test handling of connection error during WebSocket initialization"""
    websocket.send_json({"invalid-messsage": "here"})
    websocket.send_json({"type": GQLMessageType.PING})
    response = websocket.receive_json()
    assert response == {"type": GQLMessageType.PONG}


async def test_connection_invalid_subscribe(websocket):
    """Test handling of connection error during WebSocket initialization"""
    websocket.send_json(
        {
            "id": "sub2",
            "type": GQLMessageType.SUBSCRIBE,
            "payload": {"missing-query": "here"},
        }
    )
    response = websocket.receive_json()
    assert response == {
        "id": "sub2",
        "type": GQLMessageType.ERROR,
        "payload": [{"message": "No query provided"}],
    }


async def test_connection_registration(mocker):
    """Test that connections are properly registered and managed"""
    manager = SubscriptionManager()
    mock_websocket = mocker.MagicMock(spec=WebSocket)

    # Register first connection
    connection_id1 = str(uuid.uuid4())
    manager.register_connection(connection_id1, mock_websocket)

    # Verify we can get subscription info for the connection
    assert manager.get_active_subscriptions(connection_id1) == set()

    # Register second connection
    connection_id2 = str(uuid.uuid4())
    manager.register_connection(connection_id2, mock_websocket)

    # Try to register duplicate connection ID
    with pytest.raises(ValueError, match=f"Connection {connection_id1} already exists"):
        manager.register_connection(connection_id1, mock_websocket)

    # Unregister first connection
    manager.unregister_connection(connection_id1)

    # Verify first connection is gone but second remains
    assert manager.get_active_subscriptions(connection_id1) == set()
    assert manager.get_active_subscriptions(connection_id2) == set()

    # Verify we can't add subscriptions to unregistered connection
    with pytest.raises(ValueError, match=f"Connection {connection_id1} not found"):
        await manager.add_subscription(
            connection_id1, "sub1", mocker.MagicMock(), "subscription { test }"
        )


@pytest.mark.skip("causing tests to hang")
async def test_concurrent_connections(app, asgi_client):
    """Test multiple concurrent WebSocket connections with subscriptions"""
    websockets = []

    # Start multiple connections
    for _ in range(3):
        ws = asgi_client.websocket_connect(
            "/graphql", subprotocols=["graphql-transport-ws"]
        )

        # Send init message
        ws.send_json({"type": GQLMessageType.CONNECTION_INIT})
        response = ws.receive_json()
        assert response["type"] == GQLMessageType.CONNECTION_ACK

        websockets.append(ws)

    # Start subscriptions on each connection
    for i, ws in enumerate(websockets):
        ws.send_json(
            {
                "id": f"sub{i}",
                "type": GQLMessageType.SUBSCRIBE,
                "payload": {"query": "subscription { testSubscription { id } }"},
            }
        )

        # Get first message to verify subscription is working
        response = ws.receive_json()
        assert response["type"] == GQLMessageType.NEXT

    # Close first connection
    websockets[0].close()

    # Verify other connections still work
    for ws in websockets[1:]:
        ws.send_json({"type": GQLMessageType.PING})
        response = ws.receive_json()
        assert response["type"] == GQLMessageType.PONG

    # Clean up remaining connections
    for ws in websockets[1:]:
        ws.close()


async def test_subscription_cleanup_after_complete(websocket):
    """Test that subscriptions are cleaned up after completion"""
    # Connection init
    websocket.send_json({"type": GQLMessageType.CONNECTION_INIT})
    response = websocket.receive_json()
    assert response["type"] == GQLMessageType.CONNECTION_ACK

    # Start subscription
    subscription_id = "test-sub"
    websocket.send_json(
        {
            "id": subscription_id,
            "type": GQLMessageType.SUBSCRIBE,
            "payload": {"query": "subscription { testSubscription { id } }"},
        }
    )

    # Get first message
    response = websocket.receive_json()
    assert response["type"] == GQLMessageType.NEXT

    # Send complete message
    websocket.send_json({"type": GQLMessageType.COMPLETE, "id": subscription_id})

    # Verify connection still works after subscription completion
    websocket.send_json({"type": GQLMessageType.PING})
    response = websocket.receive_json()
    assert response["type"] == GQLMessageType.PONG
