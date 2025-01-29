import asyncio
import logging
from typing import AsyncIterable
from starlette.applications import Starlette
from cannula import CannulaAPI, gql
from cannula.handlers.asgi import GraphQLHandler

logging.basicConfig(level=logging.DEBUG)


schema = gql(
    """
    type Subscription {
        countdown(from_: Int!): Int!
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


# Initialize your CannulaAPI
api = CannulaAPI(
    schema=schema,
    root_value={"countdown": countdown},
)

# Create the handler
handler = GraphQLHandler(api, path="/graphql", graphiql=True)

# Create Starlette app
app = Starlette(routes=handler.routes())

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app)
