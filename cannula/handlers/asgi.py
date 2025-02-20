import asyncio
import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, Set
import uuid

from graphql import ExecutionResult, print_ast
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, Response
from starlette.routing import BaseRoute, Route, WebSocketRoute
from starlette.websockets import WebSocket, WebSocketDisconnect

from cannula import CannulaAPI
from cannula.errors import format_errors
from cannula.handlers.const import GRAPHIQL_TEMPLATE

logger = logging.getLogger(__name__)


# GraphQL over WebSocket Protocol Messages
class GQLMessageType(str, Enum):
    CONNECTION_INIT = "connection_init"
    CONNECTION_ACK = "connection_ack"
    CONNECTION_ERROR = "connection_error"
    PING = "ping"
    PONG = "pong"
    SUBSCRIBE = "subscribe"
    NEXT = "next"
    ERROR = "error"
    COMPLETE = "complete"

    def __str__(self) -> str:
        return self.value


@dataclass
class GQLMessage:
    type: str
    id: Optional[str] = None
    payload: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary, excluding None values."""
        result: Dict[str, Any] = {"type": str(self.type)}
        if self.id is not None:
            result["id"] = self.id
        if self.payload is not None:
            result["payload"] = self.payload
        return result


@dataclass
class ConnectionSubscriptions:
    """Tracks subscriptions for a single WebSocket connection"""

    websocket: WebSocket
    subscriptions: Dict[str, asyncio.Task] = field(default_factory=dict)


class SubscriptionManager:
    def __init__(self) -> None:
        # Map of connection id to subscriptions for that connection
        self._connections: Dict[str, ConnectionSubscriptions] = {}

    def register_connection(self, connection_id: str, websocket: WebSocket) -> None:
        """Register a new WebSocket connection with the provided id"""
        if connection_id in self._connections:
            raise ValueError(f"Connection {connection_id} already exists")
        self._connections[connection_id] = ConnectionSubscriptions(websocket=websocket)

    def unregister_connection(self, connection_id: str) -> None:
        """Remove a connection and clean up all its subscriptions"""
        if connection_id in self._connections:
            conn = self._connections[connection_id]
            # Cancel all subscriptions for this connection
            for task in conn.subscriptions.values():
                task.cancel()
            del self._connections[connection_id]

    async def add_subscription(
        self,
        connection_id: str,
        subscription_id: str,
        graph: "CannulaAPI",
        query: str,
        variables: Optional[Dict[str, Any]] = None,
        operation_name: Optional[str] = None,
    ) -> None:
        """Add a new subscription for a specific connection"""
        if connection_id not in self._connections:
            raise ValueError(f"Connection {connection_id} not found")

        conn = self._connections[connection_id]
        websocket = conn.websocket

        async def subscription_handler():
            try:
                result = await graph.subscribe(
                    document=query,
                    variables=variables,
                    operation_name=operation_name,
                    request=websocket,
                )

                if isinstance(result, ExecutionResult):
                    error_msg = GQLMessage(
                        type=GQLMessageType.ERROR,
                        id=subscription_id,
                        payload=format_errors(result.errors, graph.logger, graph.level),
                    )
                    await websocket.send_json(error_msg.to_dict())
                    return

                async for item in result:
                    message = GQLMessage(
                        type=GQLMessageType.NEXT,
                        id=subscription_id,
                        payload={
                            "data": item.data,
                            "errors": format_errors(
                                item.errors, graph.logger, graph.level
                            ),
                        },
                    )
                    await websocket.send_json(message.to_dict())

                # Send complete message when generator is done
                complete_msg = GQLMessage(
                    type=GQLMessageType.COMPLETE, id=subscription_id
                )
                await websocket.send_json(complete_msg.to_dict())

            except Exception as e:  # pragma: no cover
                error_msg = GQLMessage(
                    type=GQLMessageType.ERROR,
                    id=subscription_id,
                    payload=[{"message": str(e)}],
                )
                try:
                    await websocket.send_json(error_msg.to_dict())
                except Exception:
                    pass  # Connection might be already closed
            finally:
                # Remove this subscription from tracking
                if connection_id in self._connections:
                    conn = self._connections[connection_id]
                    if subscription_id in conn.subscriptions:
                        del conn.subscriptions[subscription_id]

        # Create and store the subscription task
        task = asyncio.create_task(subscription_handler())
        conn.subscriptions[subscription_id] = task

    def stop_subscription(self, connection_id: str, subscription_id: str) -> None:
        """Stop a specific subscription for a connection"""
        if connection_id in self._connections:
            conn = self._connections[connection_id]
            if subscription_id in conn.subscriptions:
                conn.subscriptions[subscription_id].cancel()
                del conn.subscriptions[subscription_id]

    def get_active_subscriptions(self, connection_id: str) -> Set[str]:
        """Get all active subscription IDs for a connection"""
        if connection_id not in self._connections:
            return set()
        return set(self._connections[connection_id].subscriptions.keys())


class GraphQLHandler:
    def __init__(
        self,
        graph: "CannulaAPI",
        path: str = "/graphql",
        graphiql: bool = True,
        graphiql_path: Optional[str] = None,
    ):
        """
        Initialize the Starlette GraphQL handler.

        Args:
            graph: CannulaAPI instance
            path: Path to serve the GraphQL endpoint
            graphiql: Whether to enable GraphiQL interface
            graphiql_path: Optional separate path for GraphiQL. If None, serves on same path as GraphQL
        """
        self.graph = graph
        self.path = path
        self.graphiql = graphiql
        self.graphiql_path = graphiql_path or path
        self.subscription_manager = SubscriptionManager()

    async def handle_request(self, request: Request) -> Response:
        if (
            request.method == "GET"
            and self.graphiql
            and request.headers.get("accept", "").find("text/html") != -1
        ):
            default = "# Welcome to Cannula write your queries here"
            operations = (
                print_ast(self.graph.operations) if self.graph.operations else None
            )
            raw_query = operations or default
            default_query = raw_query.replace("\n", "\\n")
            return HTMLResponse(
                GRAPHIQL_TEMPLATE.substitute(default_query=default_query)
            )

        if request.method not in ("POST", "GET"):
            return JSONResponse(
                {"errors": [{"message": "Method not allowed"}]}, status_code=405
            )

        try:
            variables: Optional[Dict[str, Any]] = None
            # TODO(rmyers): add coverage for this
            if request.method == "GET":  # pragma: no cover
                query = request.query_params.get("query")
                variables_params = request.query_params.get("variables")
                operation_name = request.query_params.get("operationName")

                if variables_params:
                    try:
                        variables = json.loads(variables_params)
                    except json.JSONDecodeError:
                        return JSONResponse(
                            {"errors": [{"message": "Invalid variables format"}]},
                            status_code=400,
                        )
            else:
                body = await request.json()
                query = body.get("query")
                variables = body.get("variables")
                operation_name = body.get("operationName")

            if not query:
                return JSONResponse(
                    {"errors": [{"message": "No GraphQL query found in the request"}]},
                    status_code=400,
                )

            result = await self.graph.call(
                document=query,
                variables=variables,
                operation_name=operation_name,
                request=request,
            )

            return JSONResponse(
                {
                    "data": result.data,
                    "errors": format_errors(
                        result.errors, self.graph.logger, self.graph.level
                    ),
                    "extensions": result.extensions,
                }
            )

        except json.JSONDecodeError:
            return JSONResponse(
                {"errors": [{"message": "Invalid JSON"}]}, status_code=400
            )
        except Exception as e:  # pragma: no cover
            logger.error(f"Unknown error: {e}")
            return JSONResponse({"errors": [{"message": str(e)}]}, status_code=500)

    async def handle_websocket(self, websocket: WebSocket):
        await websocket.accept(subprotocol="graphql-transport-ws")
        logger.debug("WebSocket connection accepted")

        # Generate a unique connection ID
        connection_id = str(uuid.uuid4())
        self.subscription_manager.register_connection(connection_id, websocket)

        try:
            async for raw_message in websocket.iter_json():
                logger.debug(f"Received message: {raw_message}")
                try:
                    msg = GQLMessage(**raw_message)
                except Exception as e:
                    logger.error(f"Failed to parse message: {e}")
                    continue

                if msg.type == GQLMessageType.CONNECTION_INIT:
                    # Send connection acknowledgment
                    logger.debug("Sending connection ack")
                    ack = GQLMessage(type=GQLMessageType.CONNECTION_ACK)
                    await websocket.send_json(ack.to_dict())

                elif msg.type == GQLMessageType.PING:
                    # Respond to ping with pong
                    pong = GQLMessage(type=GQLMessageType.PONG)
                    await websocket.send_json(pong.to_dict())

                elif msg.type == GQLMessageType.SUBSCRIBE and msg.id and msg.payload:
                    # Handle subscription request
                    query = msg.payload.get("query")
                    variables = msg.payload.get("variables")
                    operation_name = msg.payload.get("operationName")

                    if not query:
                        error_msg = GQLMessage(
                            type=GQLMessageType.ERROR,
                            id=msg.id,
                            payload=[{"message": "No query provided"}],
                        )
                        await websocket.send_json(error_msg.to_dict())
                        continue

                    # Let the subscription manager handle the subscription
                    await self.subscription_manager.add_subscription(
                        connection_id,
                        msg.id,
                        self.graph,
                        query,
                        variables,
                        operation_name,
                    )

                elif msg.type == GQLMessageType.COMPLETE and msg.id:
                    # Stop specific subscription when client sends complete message
                    self.subscription_manager.stop_subscription(connection_id, msg.id)

        except WebSocketDisconnect:
            # Clean up only this connection's subscriptions
            self.subscription_manager.unregister_connection(connection_id)
        except Exception as e:
            try:
                error_msg = GQLMessage(
                    type=GQLMessageType.CONNECTION_ERROR, payload={"message": str(e)}
                )
                await websocket.send_json(error_msg.to_dict())
            except Exception:  # pragma: no cover
                pass
        finally:
            try:
                # Ensure connection is unregistered and cleaned up
                self.subscription_manager.unregister_connection(connection_id)
                await websocket.close()
            except Exception:  # pragma: no cover
                pass

    def routes(self) -> list[BaseRoute]:
        """Return the list of routes to be added to a Starlette application."""
        routes = [
            Route(
                self.path,
                self.handle_request,
                # Allow all methods so we can respond with an error
                methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
            ),
            WebSocketRoute(self.path, self.handle_websocket),
        ]

        if self.graphiql and self.graphiql_path != self.path:  # pragma: no cover
            routes.append(
                Route(self.graphiql_path, self.handle_request, methods=["GET"])
            )

        return routes
