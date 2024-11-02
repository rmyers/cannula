Part3: Code Generation
======================

One of the best benefits to using a schema first approach is that it makes it incredibly
easy to parse and generate code from this well defined schema. Cannula offers a simple
way to generate data classes and resolver type definitions to assist with type hints and
making sure your code is in sync with the schema.

First we need to add some details to the `pyproject.toml` for your application:

.. literalinclude:: ../examples/tutorial/dashboard/part3/pyproject.toml

You'll notice we are including some custom Scalars in this config, we can use these in
our schema file to alter the input/output of certain fields. Cannula provides some basic
ones that are useful but you can add your own via this same config. Here is our schema
that is using the `UUID` scalar. The `UUID` Scalar will convert a string into a UUID for
output and convert a string to a `UUID` on input:

.. code-block:: graphql

    scalar UUID

    interface Persona {
        id: UUID!
        name: String
        email: String
    }

    type User implements Persona {
        id: UUID!
        name: String
        email: String
        quota: [Quota]
    }

    type Admin implements Persona {
        id: UUID!
        name: String
        email: String
    }

Now we just need to run the codegen command in this folder to generate the base types:

.. code-block:: bash

    $ cannula codegen

This will create the `_generated.py` file that we set in the `pyproject.toml`:

.. literalinclude:: ../examples/tutorial/dashboard/part3/_generated.py

For each `type` in our schema cannula generates a dataclass and a TypedDict. Then it
creates Protocols for the resolvers with the correct signature. For example the
`peopleQuery` will return a list of `PersonaTypes` which is an 'interface' that both
the `AdminType` and `UserType` satisfy. This will ensure that our `RootValue` will have
the correct signature and return values and our editor will highlight these errors.

While not technically needed it is good practice to use the GraphQLContext to hold a
reference to all the data sources for our application. Here we need a way to make database
queries to locate users for the `peopleQuery`. Our example application has a `UserRepository`
which requires a sqlalchemy session object. In this example `Context` we provide access to
`UserRespository` via a cached_property to ensure that it is lazy loaded only when we
actually use it.

.. literalinclude:: ../examples/tutorial/dashboard/part3/context.py

Next we need to make concrete classes for our base types. This isn't required either but
we can use these classes to map our types to our sqlalchemy models. You might be tempted
to just use the ORM models but it will only work for the most basic models. For anything
complex you will need this wrapper model to handle serialization with the GraphQL engine.

We can use the `DBMixin` which will assist mapping a sqlalchemy ORM model to our generated
classes. This mixin provides a `from_db` constructor and stores a reference to the original
as `_db_model`. Here is a simple example:

.. literalinclude:: ../examples/tutorial/dashboard/part3/models.py

Now that we have models and context wired up we just need our resolver for `peopleQuery`
then we can connect this to our graphql application:

.. literalinclude:: ../examples/tutorial/dashboard/part3/graph.py

Finally we need to connect our application to an endpoint so we can access this. We will
use cannula contrib dependency for FastAPI that will handle converting the request body
into a graphql request (query, variables, operationName). This dependency returns a
callable which we can use to inject our custom context.

.. literalinclude:: ../examples/tutorial/dashboard/part3/routes.py

We can use the apollo sandbox to test this out, first run the following:

.. code-block:: bash

    $ make initdb
    $ make addusers
    $ make run

This will start up the application locally with a few test users next go to the Apollo
sandbox:

https://studio.apollographql.com/sandbox/explorer/

Change the connection url to `http://localhost:8000/part3/graph`

Once it loads you should see your schema and you can try the following query:

.. code-block:: graphql

    query ExampleQuery {
        people {
            ... on User {
                email
                id
            }
            ... on Admin {
                email
                id
            }
        }
    }

This should return something like this:

.. code-block:: javascript

    {
        "data": {
            "people": [
            {
                "email": "user@email.com",
                "id": "683f89e1-b9e2-4af8-bb7e-7b2bccfe54a3"
            },
            {
                "email": "admin@example.com",
                "id": "3332ec67-8a38-4255-a09b-e31b2d0593cc"
            }
            ]
        },
        "errors": null,
        "extensions": null
    }