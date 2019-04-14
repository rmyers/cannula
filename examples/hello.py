import asyncio
import typing
import sys

import cannula

SCHEMA = cannula.gql("""
  type Message {
    text: String
  }
  type Query {
    hello(who: String): Message
  }
""")

api = cannula.API(__name__, schema=SCHEMA)


class Message(typing.NamedTuple):
    text: str


# The query resolver takes a source and info objects and any arguments
# defined by the schema. Here we only accept a single argument `who`.
@api.resolver('Query')
async def hello(source, info, who):
    return Message(f"Hello, {who}!")

# Pre-parse your query to speed up your requests. Here is an example of how
# to pass arguments to your query functions.
SAMPLE_QUERY = cannula.gql("""
  query HelloWorld ($who: String!) {
    hello(who: $who) {
      text
    }
  }
""")


who = 'world'
if len(sys.argv) > 1:
    who = sys.argv[1]

print(api.call_sync(SAMPLE_QUERY, variables={'who': who}))
