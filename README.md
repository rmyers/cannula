# Cannula

[![CircleCI](https://circleci.com/gh/rmyers/cannula.svg?style=shield)](https://circleci.com/gh/rmyers/cannula)
[![Documentation Status](https://readthedocs.org/projects/cannula/badge/?version=latest)](https://cannula.readthedocs.io/en/latest/?badge=latest)

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
just a few core libraries you can increase productivity and make your
application easier to maintain.

Our Philosophy:
1. Make your site easy to maintain.
2. Document your code.
3. Don't lock yourself into a framework.
4. Be happy!

<h2 id="install">Installation</h2>

Requires Python 3.6 or greater! The only dependency is
[graphql-core-next](https://graphql-core-next.readthedocs.io/en/latest/).

```bash
pip3 install cannula
```

<h2 id="start">Quick Start</h2>

Here is a small [hello world example](examples/hello.py):

```python
import logging
import typing
import sys

import cannula
from cannula.middleware import DebugMiddleware

SCHEMA = cannula.gql("""
  type Message {
    text: String
  }
  type Query {
    hello(who: String): Message
  }
""")

logging.basicConfig(level=logging.DEBUG)

api = cannula.API(
  __name__,
  schema=SCHEMA,
  middleware=[
    DebugMiddleware()
  ]
)


class Message(typing.NamedTuple):
    text: str


# The query resolver takes a source and info objects
# and any arguments defined by the schema. Here we
# only accept a single argument `who`.
@api.resolver('Query')
async def hello(source, info, who):
    return Message(f"Hello, {who}!")

# Pre-parse your query to speed up your requests.
# Here is an example of how to pass arguments to your
# query functions.
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
```

Now you should see the results if you run the sample on the command line:

```bash
$ python3 examples/hello.py
DEBUG:asyncio:Using selector: KqueueSelector
DEBUG:cannula.schema:Adding default empty Mutation type
DEBUG:cannula.middleware.debug:Resolving Query.hello expecting type Message
DEBUG:cannula.middleware.debug:Field Query.hello resolved: Message(text='Hello, world!') in 0.000108 seconds
DEBUG:cannula.middleware.debug:Resolving Message.text expecting type String
DEBUG:cannula.middleware.debug:Field Message.text resolved: 'Hello, world!' in 0.000067 seconds
ExecutionResult(
  data={'hello': {'text': 'Hello, world!'}},
  errors=None
)

$ python3 examples/hello.py Bob
DEBUG:asyncio:Using selector: KqueueSelector
DEBUG:cannula.schema:Adding default empty Mutation type
DEBUG:cannula.middleware.debug:Resolving Query.hello expecting type Message
DEBUG:cannula.middleware.debug:Field Query.hello resolved: Message(text='Hello, Bob!') in 0.000104 seconds
DEBUG:cannula.middleware.debug:Resolving Message.text expecting type String
DEBUG:cannula.middleware.debug:Field Message.text resolved: 'Hello, Bob!' in 0.000101 seconds
ExecutionResult(
  data={'hello': {'text': 'Hello, Bob!'}},
  errors=None
)
```

But what about Django integration or flask?

```python
# pip install channels, Django
import cannula
from channels.db import database_sync_to_async
from django.contrib.auth.models import User

schema = cannula.gql("""
  type User {
    username: String   # Only expose the fields you actually use
    first_name: String
    last_name: String
    made_up_field: String
  }
  extend type Query {
    getUserById(user_id: String): User
  }
""")

@api.query()
async def getUserById(source, info, user_id):
    return await get_user(user_id)

@database_sync_to_async
def get_user(user_id):
    return User.objects.get(pk=user_id)

@api.resolve('User')
async def made_up_field(source, info):
    return f"{source.get_full_name()} is a lying lier there is no 'made_up_field'"
```

Since GraphQL is agnostic about where or how you store your data all you need
to do is provide a function to resolve a query. The results you return just
need to match the schema and you are done.

Django and sqlalchemy already provide tools to query the database. And they
work quite well. Or you may choose to use an async database library to make
concurrent requests work even better. Try them all and see what works best for
your team and your use case.

<h2 id="examples">Examples and Documentation</h2>

* [hello world](examples/hello.py)
* [using mocks](examples/mocks.py)
* [Real World Example](examples/cloud)

[Documentation](https://cannula.readthedocs.io/)
