import asyncio
import logging
from typing import Any, AsyncIterable
from starlette.applications import Starlette
from cannula import gql
from cannula.handlers.asgi import GraphQLHandler
from cannula.contrib.otel import create_instrumented_api, trace_middleware

logging.basicConfig(level=logging.DEBUG)


schema = gql(
    """
    type Frank {
        name: String
        email: String
    }
    type Subscription {
        countdown(from_: Int!): Int!
    }
    type Query {
        frank: Frank
    }
"""
)


class AsyncRange:
    def __init__(self, start, end):
        self.start = start
        self.end = end

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.start > self.end:
            await asyncio.sleep(1)
            value = self.start
            self.start -= 1
            return value
        else:
            raise StopAsyncIteration


async def countdown(info, from_: int) -> AsyncIterable[dict]:
    async for i in AsyncRange(from_, -1):
        yield {"countdown": i}


class Frank:
    name = "frankie"

    @staticmethod
    async def email(info) -> str:
        return "123@franks.com"


async def frank(info) -> Any:
    return Frank


# Initialize your CannulaAPI
api = create_instrumented_api(
    schema=schema,
    root_value={"countdown": countdown, "frank": frank},
    middleware=[trace_middleware],
)

# Create the handler
handler = GraphQLHandler(api, path="/graphql", graphiql=True)

# Create Starlette app
app = Starlette(routes=handler.routes())

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app)
