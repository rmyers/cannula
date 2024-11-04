Part2: Resolvers
================

In order to use our graph we need to connect the schema to our code.
When the graph is parsed the type objects do not have any implemention we
need to tell graphql how to resolve it. The easiest way to do this is to
set the `root_value` to a mapping of operation names to functions.

The functions we will add can be async functions that must accept at
least one argment for the `GraphQLResolveInfo`. This holds the schema
and query information along with the `context` that is generated for
each request and is a place to read and write data to pass to other
resolvers in the query. Typically this is just the request data like
`Authorization` headers, but could be anything. In our example we will
use `cannula.ResolveInfo` which is a subclass that adds some functionality
we will use later.

The resolvers can return objects or dictionaries as long as they are the
correct 'shape'. For us that means there should be `id`, `name`, and `email`:

For organization we'll move the GraphQL application and resolvers into a
separate module `graph.py`:

.. code-block:: python

    import pathlib
    import cannula

    from dashboard.core.config import config

    async def resolve_me(info: cannula.ResolveInfo):
        return {
            "name": "Tiny Tim",
            "email": "tim@example.com",
            "id": "1",
        }

    cannula_app = cannula.CannulaAPI(
        schema=pathlib.Path(config.root / "part1"),
        root_value={"me": resolve_me},
    )

The root route and template remain the same except for moving the `graphql`
application. You can view the results: http://localhost:8000/part2/ and see that
we get an error now:

.. code-block:: python

    errors=[
        GraphQLError(
            "Abstract type 'Persona' must resolve to an Object type at runtime for field 'Query.me'. Either the 'Persona' type should provide a 'resolve_type' function or each possible type should provide an 'is_type_of' function.",
            locations=[SourceLocation(line=3, column=9)],
            path=['me'],
        )
    ]

.. note:: In the tutorial source we have the following fix applied so you will not see the error.

Since our query result is an `Interface` we need to tell GraphQL what type our
object is. As the error states there are a couple ways to fix this. The easiest
way is to provide a `__typename` field in the results since we are not returning
an object that can functions added. The error assumes you have GraphQL type objects
defined which with schema first we do not have (yet).

.. code-block:: python

    import pathlib
    import cannula

    from dashboard.core.config import config

    async def resolve_me(info: cannula.ResolveInfo):
        return {
            "__typename": "User",
            "name": "Tiny Tim",
            "email": "tim@example.com",
            "id": "1",
        }

    cannula_app = cannula.CannulaAPI(
        schema=pathlib.Path(config.root / "part1"),
        root_value={"me": resolve_me},
    )

Now we get the results we wanted::

    Results:

    ExecutionResult(data={'me': {'id': '1', 'name': 'Tiny Tim'}}, errors=None)


This is great but seems like a ton of boilerplate we need to add. Luckily since we
have done all the work to define our schema with types we can use this to auto generate
code.

In the frontend world you can use GraphQL Codegen to create types and React hooks
with Cannula we can do the same for your backend code.

Go to :doc:`part3` to see this in action.