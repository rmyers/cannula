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
`Authorization` headers, but could be anything.

The resolvers can return objects or dictionaries as long as they are the
correct 'shape'. For us that means there should be `id`, `name`, and `email`:

.. code-block:: python

    async def resolve_me(info: GraphQLResolveInfo):
        return {"name": "Tiny Tim", "email": "tim@example.com", "id": "1"}