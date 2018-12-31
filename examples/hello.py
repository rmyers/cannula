import asyncio
import typing
import sys

import cannula

my_schema = """
  type Message {
    text: String
  }
  extend type Query {
    hello(who: String): Message
  }
"""

api = cannula.API(__name__, schema=my_schema)


# The graphql-core-next library by default expects an object as the response
# to do attribute lookups to resolve the fields..
class Message(typing.NamedTuple):
    text: str


# The query resolver takes a source and info objects and any arguments
# defined by the schema. Here we only accept a single argument `who`.
@api.query()
async def hello(source, info, who):
    return Message(f"Hello, {who}!")


async def main():
    who = 'world'
    if len(sys.argv) > 1:
        who = sys.argv[1]
    # An example of a query that would come in the body of an http request.
    # When using a format string we need to escape the literal `{` with `{{`.
    sample_query = f"""{{
      hello(who: "{who}") {{
        text
      }}
    }}
    """
    results = await api.call(sample_query)
    print(results)

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
