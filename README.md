# Cannula

> GraphQL for people who like Python!

* [Why Cannula](#why)
* [Installation](#install)
* [Quick Start](#start)
* [Documentation](#docs)

<h2 id="why">Why Cannula?</h2>

We wanted to make the world a better place, but we are programmers so we settled
on making the web fun again. Too much attention has been given to Javascript
client libraries. They all seem to compete on size and speed and features but
most of them do not solve any of the actual problems you have. So while the
todo application is quick and easy to follow the hard parts take a long time
to complete. For starters Javascript use to be simple and it did not require
using a transpiler. It was mostly JQuery and it sort of worked but it didn't
get in your way.

Now a days if you want a fancy single page application you need to invest a
good week or so planning out all the tools you will need to assemble your site.
Every decision is full of sorrow and doubt as you google for the latest trends
or how to setup unit tests. Or searching for a bootstrapped version of the
library you like.

Say for example you want to have hot reloading developer experience you need
to organize your code in a way that allows this to work. If you are familiar
with python web applications they usually have a dev mode that you can start.
With webpack and parsel you can have the hot reloading but that doesn't play
well with your python library. So you have to either do tricks or just give
up complete control to your client side Javascript. It is just not easy to
have a simple web page served by a python web framework along side your
dynamic pages that require a ton of interaction.

Why did we let the Javascript developers take over all this control out from
under our noses?

Cannula is our way of taking back the web. What if I told you, you can have
your cake and eat it too? Too good to be true? No it is all possible with a
few simple tools and you can rescue your sanity once again. The best part is
as the javascript becomes smaller you have greater control over the page speed
once again. React and others can now do server side rendering to reduce the
amount of time it takes to render a page. But you can achieve the same boost
in speed boost using Cannula. All without having to run node.

Is Cannula unique or only for Python?

No, while Cannula is for python if you read the book you will notice that
there is nothing specific about Python that is required. The magic all happens
with graphql. You can use any language you want as your graphql server. We just
happen to like Python so we wrote a framework to make it easy to replicate our
designs.

At the heart of it graphql is the glue holding the system together how you
inject data into graphql is entirely up to you. And how little you use is up
to you too. It could be that you really like managing 1500 npm modules just
so that you can render :ghost: gifs on the webpack command line. I guess what
ever floats your boat. If you are like me and don't want to be dependant on
*EVERYTHING* working (yarn.lock file?) then you should reduce the number of
libraries you use. That includes this one, don't use it if all you need is a
single page.

Our Philosophy:
1. Make your site easy to maintain.
2. Document your code.
3. Don't lock yourself into a framework.
4. Be happy!

<h2 id="install">Installation</h2>

Requires Python 3.6 or greater!

```bash
pip3 install cannula
```

<h2 id="start">Quick Start</h2>

Here is a small [hello world example](examples/hello.py):

```python
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
# to do attribute lookups to resolve the fields.
class Message(typing.NamedTuple):
    text: str

# The query resolver takes a source and info objects and any arguments
# defined by the schema. Here we only accept a single argument `who`.
@api.resolver('Query')
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
```

Now you should see the results if you run the sample on the command line:

```bash
$ PYTHONPATH=. python3 examples/hello.py
ExecutionResult(data={'hello': {'text': 'Hello, world!'}}, errors=None)
$ PYTHONPATH=. python3 examples/hello.py Bob
ExecutionResult(data={'hello': {'text': 'Hello, Bob!'}}, errors=None)
```

But what about Django integration or flask?

```python

from django.contrib.auth.models import User

schema = """
  type User {
    username: String   # Only expose the fields you actually use
    first_name: String
    last_name: String
    made_up_field: String
  }
  extend type Query {
    getUserById(user_id: String): User
  }
"""

@api.query()
async def getUserById(source, info, user_id):
    return User.objects.get(pk=user_id)

@api.resolve('User')
async def made_up_field(source, info):
    return f"{source.get_full_name()} is a lying lier there is no 'made_up_field'"
```

Since cannula is agnostic about where or how you store your data all you need
to do is provide a function to resolve a query. The results you return just
need to match the schema and you are done.

Django and sqlalchemy already provide tools to query the database. And they
work quite well. Or you could just use a raw db connection if you'd prefer.

The beauty of the above example is you only need to expose the fields you
want to and there is nothing about that schema which is specific to Django
or cannula. Compare this to a framework like graphene-django which you need
to specify the fields you want exposed and other various properties.

This isn't to say that graphene is bad, if it fits your use case and is simple
for you to manage then by all means use it. The problem is that your UI is
probably not a simple one to one mapping of your database. GraphQL is
specifically designed to reduce the complexity of the UI. If you just bolt
it onto your database models you are doing it wrong.

<h2 id="docs">Documentation</h2>

We pride ourselves on having through documentation, explaining our reasons for
all the decissions we made. We wrote a whole book before we wrote a single line
of code!

[Cannula Documentation](./docs)
