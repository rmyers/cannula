import sys
from typing import Optional, Dict, Any, AsyncGenerator
import json
import asyncio
import logging
from dataclasses import dataclass
from enum import Enum
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, Response
from starlette.routing import Route, WebSocketRoute
from starlette.websockets import WebSocket, WebSocketDisconnect

from cannula import CannulaAPI

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)


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


@dataclass
class GQLMessage:
    type: str
    id: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None


GRAPHIQL_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>GraphiQL</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/graphiql/2.4.7/graphiql.min.css" rel="stylesheet" />
</head>
<body style="margin: 0; height: 100vh;">
    <div id="graphiql" style="height: 100vh;"></div>
    <script
        crossorigin
        src="https://cdnjs.cloudflare.com/ajax/libs/react/18.2.0/umd/react.production.min.js"
    ></script>
    <script
        crossorigin
        src="https://cdnjs.cloudflare.com/ajax/libs/react-dom/18.2.0/umd/react-dom.production.min.js"
    ></script>
    <script
        crossorigin
        src="https://cdnjs.cloudflare.com/ajax/libs/graphiql/2.4.7/graphiql.min.js"
    ></script>
    <script>
        const fetcher = GraphiQL.createFetcher({
            url: window.location.href,
            subscriptionUrl: 'ws://' + window.location.host + window.location.pathname,
        });
        ReactDOM.render(
            React.createElement(GraphiQL, {
                fetcher: fetcher,
                defaultQuery: "# Write your query here",
            }),
            document.getElementById('graphiql'),
        );
    </script>
</body>
</html>
"""


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
            result = await graph.call(
                document=query,
                variables=variables,
                operation_name=operation_name,
                request=websocket,
            )

            if hasattr(result, "errors") and result.errors:
                error_msg = GQLMessage(
                    type=GQLMessageType.ERROR,
                    id=subscription_id,
                    payload={"errors": result.errors},
                )
                logger.error(str(error_msg))
                await websocket.send_json(error_msg.__dict__)
                return

            if result.data:
                # Handle the AsyncGenerator for subscriptions
                if isinstance(result.data, dict) and any(
                    isinstance(v, AsyncGenerator) for v in result.data.values()
                ):
                    # Get the first generator from the data dict
                    field_name, generator = next(
                        (k, v)
                        for k, v in result.data.items()
                        if isinstance(v, AsyncGenerator)
                    )

                    async for item in generator:
                        message = GQLMessage(
                            type=GQLMessageType.NEXT,
                            id=subscription_id,
                            payload={"data": {field_name: item}},
                        )
                        await websocket.send_json(message.__dict__)

                    # Send complete message when generator is done
                    complete_msg = GQLMessage(
                        type=GQLMessageType.COMPLETE, id=subscription_id
                    )
                    await websocket.send_json(complete_msg.__dict__)
                else:
                    # Handle non-subscription queries over websocket
                    message = GQLMessage(
                        type=GQLMessageType.NEXT,
                        id=subscription_id,
                        payload={"data": result.data},
                    )
                    await websocket.send_json(message.__dict__)

                    complete_msg = GQLMessage(
                        type=GQLMessageType.COMPLETE, id=subscription_id
                    )
                    await websocket.send_json(complete_msg.__dict__)

            if result.errors:
                error_msg = GQLMessage(
                    type=GQLMessageType.ERROR,
                    id=subscription_id,
                    payload={"errors": result.errors},
                )
                await websocket.send_json(error_msg.__dict__)

        except Exception as e:
            error_msg = GQLMessage(
                type=GQLMessageType.ERROR,
                id=subscription_id,
                payload={"errors": [{"message": str(e)}]},
            )
            await websocket.send_json(error_msg.__dict__)
        finally:
            if subscription_id in self.active_subscriptions:
                del self.active_subscriptions[subscription_id]

    def stop_subscription(self, subscription_id: str):
        if subscription_id in self.active_subscriptions:
            self.active_subscriptions[subscription_id].cancel()
            del self.active_subscriptions[subscription_id]


class StarletteGraphQLHandler:
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

        logger.info("Handling request")
        try:
            if request.method == "GET":
                query = request.query_params.get("query")
                variables = request.query_params.get("variables")
                operation_name = request.query_params.get("operationName")

                if variables:
                    try:
                        variables = json.loads(variables)
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
                    "errors": result.errors,
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
        logger.info(str(websocket))
        await websocket.accept(subprotocol="graphql-transport-ws")
        logger.info("WebSocket connection accepted")

        try:
            # Wait for connection init message
            async for raw_message in websocket.iter_json():
                logger.info(f"Received message: {raw_message}")
                try:
                    msg = GQLMessage(**raw_message)
                except Exception as e:
                    logger.error(f"Failed to parse message: {e}")
                    continue

                if msg.type == GQLMessageType.CONNECTION_INIT:
                    # Send connection acknowledgment
                    logger.info("Sending connection ack")
                    ack = GQLMessage(type=GQLMessageType.CONNECTION_ACK)
                    await websocket.send_json(ack.__dict__)

                elif msg.type == GQLMessageType.PING:
                    # Respond to ping with pong
                    pong = GQLMessage(type=GQLMessageType.PONG)
                    await websocket.send_json(pong.__dict__)

                elif msg.type == GQLMessageType.SUBSCRIBE and msg.id and msg.payload:
                    # Handle subscription request
                    query = msg.payload.get("query")
                    variables = msg.payload.get("variables")
                    operation_name = msg.payload.get("operationName")

                    if not query:
                        error_msg = GQLMessage(
                            type=GQLMessageType.ERROR,
                            id=msg.id,
                            payload={"errors": [{"message": "No query provided"}]},
                        )
                        await websocket.send_json(error_msg.__dict__)
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
            logger.exception("WebSocket handler error")
            try:
                error_msg = GQLMessage(
                    type=GQLMessageType.CONNECTION_ERROR, payload={"message": str(e)}
                )
                await websocket.send_json(error_msg.__dict__)
            except:
                pass
        finally:
            try:
                await websocket.close()
            except:
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


# Example usage:
"""
from starlette.applications import Starlette
from cannula import CannulaAPI

# Initialize your CannulaAPI with subscription support
api = CannulaAPI(schema='''
    type Subscription {
        countdown(from: Int!): Int!
    }
''')

@api.resolver('Subscription')
async def countdown(root, info, from_: int) -> AsyncGenerator[int, None]:
    for i in range(from_, -1, -1):
        yield i
        await asyncio.sleep(1)

# Create the handler
handler = StarletteGraphQLHandler(api, path="/graphql", graphiql=True)

# Create Starlette app
app = Starlette(routes=handler.routes())
"""
