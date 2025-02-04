# Cannula

[![CircleCI](https://circleci.com/gh/rmyers/cannula.svg?style=shield)](https://circleci.com/gh/rmyers/cannula)
[![Documentation Status](https://readthedocs.org/projects/cannula/badge/?version=main)](https://cannula.readthedocs.io/en/main/?badge=main)
[![codecov](https://codecov.io/gh/rmyers/cannula/branch/main/graph/badge.svg?token=4OOWACS3QD)](https://codecov.io/gh/rmyers/cannula)

> GraphQL for people who like Python!

- [Why Cannula](#why)
- [Installation](#install)
- [Quick Start](#start)
- [Performance](#performance)
- [Examples](#examples)
- [Documentation](https://cannula.readthedocs.io/)

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

Requires Python 3.10 or greater! The only dependency is
[graphql-core](https://graphql-core-3.readthedocs.io/en/latest/).

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

# The query resolver takes an `info` object and any arguments
# defined by the schema. Here we only accept a single argument `who`.
async def hello(
    info: cannula.ResolveInfo,
    who: str,
) -> str:
    # Here the field_name is 'hello' so we'll
    # return 'hello {who}!'
    return f"{info.field_name} {who}!"


# Basic API setup with the schema we defined and root_value
api = cannula.CannulaAPI(
    schema=SCHEMA,
    root_value={
        "hello": hello,  # Set the resolver function we defined
    }
)


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

<h2 id="performance">Performance</h2>

We try to make sure cannula is as fast as possible. While real world benchmarks are always difficult we do have a simple test that attempts to show how cannula performs against other setups.

You can view the tests in [performance](performance/test_performance.py). We have a simple function that returns data then compare the time it takes to return those results with a plan FastAPI app vs a GraphQL request. Then we try the same GraphQL request in both Cannula and Ariadne. Here is a sample of the output:

```
1000 iterations (lower is better)

test_performance.py::test_performance
performance test results:
fastapi: 0.4401752959993246
ariadne results: 1.8754248120003467
cannula results: 0.5984569250003915
PASSED
test_performance.py::test_performance_invalid_request
performance test results:
fastapi: 0.3655707629995959
ariadne results: 0.8345384459998968
cannula results: 0.42288053700031014
PASSED
test_performance.py::test_performance_invalid_query
performance test results:
fastapi: 0.3692567819998658
ariadne results: 2.08707908300039
cannula results: 0.4372879369993825
PASSED
```

As you can see Cannula is close to the raw performance of FastAPI. Granted real world results might be different as the way Cannula achieves it speed is by caching query validation results. This works best if you have a relatively fixed set of queries that are performed such as a UI that you or another team manages. If the requests are completely ad hoc like a public api then the results will not be as great.

<h2 id="examples">Examples and Documentation</h2>

- [hello world](examples/hello.py)

[Documentation](https://cannula.readthedocs.io/)
