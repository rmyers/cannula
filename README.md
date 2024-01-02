# Cannula

[![CircleCI](https://circleci.com/gh/rmyers/cannula.svg?style=shield)](https://circleci.com/gh/rmyers/cannula)
[![Documentation Status](https://readthedocs.org/projects/cannula/badge/?version=main)](https://cannula.readthedocs.io/en/main/?badge=main)

> GraphQL for people who like Python!

* [Why Cannula](#why)
* [Installation](#install)
* [Quick Start](#start)
* [Examples](#examples)
* [Documentation](https://cannula.readthedocs.io/)

<h2 id="why">Why Cannula?</h2>

We wanted to make the world a better place, but we are programmers so we settled
on making the web fun again. Too much attention has been given to Javascript
client libraries. They all seem to compete on size and speed and features but
most of them do not solve any of the actual problems you have. So while the
todo application is quick and easy to follow the hard parts take a long time
to complete.

Now a days if you want a fancy single page application you need to invest a
good week or so planning out all the tools you will need to assemble your site.
Every decision is full of sorrow and doubt as you google for the latest trends
or how to setup unit tests. Or searching for a bootstrapped version of the
library you like.

Using GraphQL you can simplify your web application stack and reduce
dependencies to achieve the same customer experience without regret. By using
a schema to define your application you can auto generate much of the code
you need to interact with it.

Our Philosophy:
1. Make your site easy to maintain.
2. Document your code.
3. Don't lock yourself into a framework.
4. Be happy!

<h2 id="install">Installation</h2>

Requires Python 3.8 or greater! The only dependency is
[graphql-core-next](https://graphql-core-next.readthedocs.io/en/latest/).

```bash
pip3 install cannula
```

<h2 id="start">Quick Start</h2>

Here is a small [hello world example](examples/hello.py):

```python
import typing
import sys

import cannula

SCHEMA = """
    type Query {
        hello(who: String!): String
    }
"""

# Basic API setup with the schema we defined
api = cannula.API(schema=SCHEMA)


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


def run_hello(who: str = "world"):
    return api.call_sync(SAMPLE_QUERY, variables={"who": who})


if __name__ == "__main__":
    who = "world"
    if len(sys.argv) > 1:
        who = sys.argv[1]

    print(run_hello(who))

```

Now you should see the results if you run the sample on the command line:

```
$ python3 examples/hello.py
ExecutionResult(
  data={'hello': "hello world!"},
  errors=None
)

$ python3 examples/hello.py Bob
ExecutionResult(
  data={"hello": "hello Bob!"},
  errors=None
)
```

<h2 id="examples">Examples and Documentation</h2>

* [hello world](examples/hello.py)
* [using mocks](examples/mocks.py)

[Documentation](https://cannula.readthedocs.io/)
