import asyncio
import typing
import sys

import cannula

SCHEMA = """
    type Query {
        hello(who: String!): String
    }
"""

# Basic API setup with the schema we defined
api = cannula.CannulaAPI(schema=SCHEMA)


# The query resolver takes a `source` and `info` objects
# and any arguments defined by the schema. Here we
# only accept a single argument `who`.
@api.query()
async def hello(
    source: typing.Any,
    info: cannula.ResolveInfo,
    who: str,
) -> str:
    # Here the field_name is 'hello' so we'll
    # return 'hello {who}!'
    return f"{info.field_name} {who}!"


# Pre-parse your query to speed up your requests.
SAMPLE_QUERY = cannula.gql(
    """
    query HelloWorld ($who: String!) {
        hello(who: $who)
    }
"""
)


async def run_hello(who: str = "world"):
    results = await api.call(SAMPLE_QUERY, variables={"who": who})
    print(results.data)
    return results.data


if __name__ == "__main__":
    who = "world"
    if len(sys.argv) > 1:
        who = sys.argv[1]

    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_hello(who))
