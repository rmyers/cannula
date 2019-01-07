import asyncio
import typing
import sys

from graphql.language import parse

import cannula

api = cannula.API(__name__, schema="""
  type Message {
    text: String
  }
  extend type Query {
    hello(who: String): Message
  }
""")


class Message(typing.NamedTuple):
    text: str


# The query resolver takes a source and info objects and any arguments
# defined by the schema. Here we only accept a single argument `who`.
@api.resolver('Query')
async def hello(source, info, who):
    return Message(f"Hello, {who}!")

# Pre-parse your query to speed up your requests. Here is an example of how
# to pass arguments to your query functions.
SAMPLE_QUERY = parse("""
  query HelloWorld ($who: String!) {
    hello(who: $who) {
      text
    }
  }
""")


async def main():
    who = 'world'
    if len(sys.argv) > 1:
        who = sys.argv[1]

    results = await api.call(SAMPLE_QUERY, variables={'who': who})
    print(results)

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
