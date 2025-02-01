import asyncio
import json
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any

from graphql import ExecutionResult
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, Response
from starlette.routing import Route, WebSocketRoute
from starlette.websockets import WebSocket, WebSocketDisconnect

from cannula import CannulaAPI, format_errors
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

    def __str__(self):
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


class SubscriptionManager:
    def __init__(self):
        self.active_subscriptions: Dict[str, asyncio.Task] = {}

    async def add_subscription(
        self,
        subscription_id: str,
        websocket: WebSocket,
        graph: CannulaAPI,
        query: str,
        variables: Optional[Dict[str, Any]] = None,
        operation_name: Optional[str] = None,
    ):
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
                        "errors": format_errors(item.errors, graph.logger, graph.level),
                    },
                )
                await websocket.send_json(message.to_dict())

            # Send complete message when generator is done
            complete_msg = GQLMessage(type=GQLMessageType.COMPLETE, id=subscription_id)
            await websocket.send_json(complete_msg.to_dict())

        except Exception as e:
            error_msg = GQLMessage(
                type=GQLMessageType.ERROR,
                id=subscription_id,
                payload=[{"message": str(e)}],
            )
            await websocket.send_json(error_msg.to_dict())
        finally:
            if subscription_id in self.active_subscriptions:
                del self.active_subscriptions[subscription_id]

    def stop_subscription(self, subscription_id: str):
        if subscription_id in self.active_subscriptions:
            self.active_subscriptions[subscription_id].cancel()
            del self.active_subscriptions[subscription_id]


class GraphQLHandler:
    def __init__(
        self,
        graph: CannulaAPI,
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
            return HTMLResponse(GRAPHIQL_TEMPLATE)

        if request.method not in ("POST", "GET"):
            return JSONResponse(
                {"errors": [{"message": "Method not allowed"}]}, status_code=405
            )

        try:
            variables: Optional[Dict[str, Any]] = None
            if request.method == "GET":
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
        except Exception as e:
            return JSONResponse({"errors": [{"message": str(e)}]}, status_code=500)

    async def handle_websocket(self, websocket: WebSocket):
        await websocket.accept(subprotocol="graphql-transport-ws")
        logger.debug("WebSocket connection accepted")

        try:
            # Wait for connection init message
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

                    # Create and store subscription task
                    task = asyncio.create_task(
                        self.subscription_manager.add_subscription(
                            msg.id,
                            websocket,
                            self.graph,
                            query,
                            variables,
                            operation_name,
                        )
                    )
                    self.subscription_manager.active_subscriptions[msg.id] = task

                elif msg.type == GQLMessageType.COMPLETE and msg.id:
                    # Stop subscription when client sends complete message
                    self.subscription_manager.stop_subscription(msg.id)

        except WebSocketDisconnect:
            # Clean up all subscriptions for this connection
            for subscription_id in list(
                self.subscription_manager.active_subscriptions.keys()
            ):
                self.subscription_manager.stop_subscription(subscription_id)
        except Exception as e:
            try:
                error_msg = GQLMessage(
                    type=GQLMessageType.CONNECTION_ERROR, payload={"message": str(e)}
                )
                await websocket.send_json(error_msg.to_dict())
            except Exception:
                pass
        finally:
            try:
                await websocket.close()
            except Exception:
                pass

    def routes(self) -> list:
        """Return the list of routes to be added to a Starlette application."""
        routes = [
            Route(self.path, self.handle_request, methods=["GET", "POST"]),
            WebSocketRoute(self.path, self.handle_websocket),
        ]

        if self.graphiql and self.graphiql_path != self.path:
            routes.append(
                Route(self.graphiql_path, self.handle_request, methods=["GET"])
            )

        return routes
