import logging
import typing
import sys

import cannula
from cannula.middleware import DebugMiddleware
from graphql import GraphQLResolveInfo

SCHEMA = cannula.gql(
    """
    type Message {
        text: String
    }
    type Query {
        hello(who: String): Message
    }
"""
)

logging.basicConfig(level=logging.DEBUG)

api = cannula.API(
    schema=SCHEMA,
    middleware=[DebugMiddleware()],
)


class Message(typing.NamedTuple):
    text: str


# The query resolver takes a source and info objects
# and any arguments defined by the schema. Here we
# only accept a single argument `who`.
@api.resolver("Query", "hello")
async def hello(
    source: typing.Any,
    info: GraphQLResolveInfo,
    who: str,
) -> Message:
    return Message(f"Hello, {who}!")


# Pre-parse your query to speed up your requests.
# Here is an example of how to pass arguments to your
# query functions.
SAMPLE_QUERY = cannula.gql(
    """
    query HelloWorld ($who: String!) {
        hello(who: $who) {
            text
        }
    }
"""
)


who = "world"
if len(sys.argv) > 1:
    who = sys.argv[1]

print(api.call_sync(SAMPLE_QUERY, variables={"who": who}))
