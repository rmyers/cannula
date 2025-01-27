import asyncio
from typing import Any, AsyncGenerator
from starlette.applications import Starlette
from cannula import CannulaAPI
from cannula.contrib.star import StarletteGraphQLHandler

# Initialize your CannulaAPI
api = CannulaAPI(
    schema="""
    type Query {
        hello: String
    }
    type Subscription {
        countdown(from_: Int!): Int!
    }
"""
)


@api.resolver("Subscription")
async def countdown(root, info, from_: int) -> AsyncGenerator[int, None]:
    for i in range(from_, -1, -1):
        yield i
        await asyncio.sleep(1)


# Create the handler
handler = StarletteGraphQLHandler(api, path="/graphql", graphiql=True)

# Create Starlette app
app = Starlette(routes=handler.routes())

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app)
