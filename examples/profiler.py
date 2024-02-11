import asyncio
import logging
import typing

from graphql import ExecutionResult

import cannula
from cannula.middleware import ProfileMiddleware

logging.basicConfig(level=logging.DEBUG)

LOG = logging.getLogger(__name__)
SCHEMA = """
    type Query {
        prime(num: Int!): String
        hello: String
    }
"""

# Basic API setup with the schema we defined
api = cannula.API(schema=SCHEMA, middleware=[ProfileMiddleware(logger=LOG)])


async def prime(info: cannula.ResolveInfo, num: int) -> str:
    flag = False

    if num == 1:
        return f"{num} is not a prime number"
    elif num > 1:
        # check for factors
        for i in range(2, num):
            if (num % i) == 0:
                # if factor is found, set flag to True
                flag = True
                # break out of loop
                break

    prime = "is not" if flag else "is"

    return f"{num} {prime} a prime number"


def hello(
    info: cannula.ResolveInfo,
) -> str:
    return f"{info.field_name} World!"


# Basic API setup with the schema we defined
api = cannula.API(
    schema=SCHEMA,
    middleware=[ProfileMiddleware(logger=LOG)],
    root_value={"prime": prime, "hello": hello},
)

# Pre-parse your query to speed up your requests.
SAMPLE_QUERY = cannula.gql(
    """
    query PrimeWorld($n: Int!) {
        prime(num: $n)
        hello
    }
"""
)


async def main() -> ExecutionResult:
    results = await api.call(SAMPLE_QUERY, variables={"n": 17624813})
    print(results.data)
    print(results.errors)
    return results


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
