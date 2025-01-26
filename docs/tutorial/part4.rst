Part4: Related Field Resolution
===============================

In many web applications not everything fits in the same data types or structures. We
usually have a relation from one thing to another and that relation can be either hard
or soft. For instance in a relational database you might have a foreign key from a
parent to their child. That would be a hard relation and it is easy to reason about
and code up. However what if your manager asked you to find all the cousins of a given
person, well that is not so simple, the data is there but your gonna have to do a bunch
of work to get the answer.

Cannula has built into the codegen logic the concept of `Related` fields. These are fields
you want to expose on the model but you don't have an easy attribute to lookup. While it
doesn't make the work of finding cousins easier, it does make it possible to do in an easy
to follow structure. We already saw this in the generated Python, all the Query and
Mutations are examples of this. Any field that has arguments will be rendered as a function
on the base type. In the case of SQLAlchemy types if any field's return type is a SQLAlchemy
model Cannula will automatically add a resolver for it.

In some cases where there is no clear foreign key relation we must provide a `where` clause
to preform the query. This uses a `text` query to allow a great deal of flexibility to write
queries. Then Cannula will use `bindparams` to map all the graphql arguments plus any defined
by the directive. For example the graphql query arguments might include a secondary rule but
the primary lookup would be the `id` of the parent.

.. code-block:: graphql

    type User {
        id: ID!
        # imaging you have a lookup that finds the users best bestFriend
        # by some sort of ranking system
        bestFriends(ranking: Int): Friend
            @field_meta(
                # Query the 'friends' table sorted by rank
                where: "user_id = :id AND ranking >= :ranking ORDER BY ranking ASC",
                # "id" here is the id of the user aka `self.id` since this is a field
                # on the user object it does not make since to require it in the graphql
                # query but we have to tell the system which field to use to relate them.
                args: ["id"],
            )
    }

Starting with the schema from part3, we have added a new type 'Quota' that is has a foreign_key
to the 'User' type for a simple example of how the relations work:

.. literalinclude:: ../examples/tutorial/dashboard/part4/schema.graphql
    :language: graphql

Now when we run `cannula codegen` we get these types and sql:

.. literalinclude:: ../examples/tutorial/dashboard/part4/gql/types.py

.. literalinclude:: ../examples/tutorial/dashboard/part4/gql/sql.py

You can see that we have foreign_key relations in the db and our types
now have resolvers that call the context which is where all the magic happens.
let's look at the context that was generated to see our custom queries in
action:

.. literalinclude:: ../examples/tutorial/dashboard/part4/gql/context.py

Now we just need to add in the new query we added to the `RootType`:

.. literalinclude:: ../examples/tutorial/dashboard/part4/graph.py

You can now update the route to `http://localhost:8000/part4/graph` and try the following
query:

.. code-block::

    query People {
        people {
            name
            email
            quota {
                resource
                limit
            }
            overQuota(resource: "water") {
                count
            }
        }
    }

And get results like this:

.. code-block:: javascript

    {
        "data": {
            "people": [
            {
                "name": "Normal User",
                "email": "user@email.com",
                "quota": [
                {
                    "resource": "fire",
                    "limit": 10
                },
                {
                    "resource": "water",
                    "limit": 15
                }
                ],
                "overQuota": {
                "count": 4
                }
            },
            {
                "name": "Admin User",
                "email": "admin@example.com",
                "quota": [
                {
                    "resource": "fire",
                    "limit": 5
                }
                ],
                "overQuota": null
            }
            ]
        },
        "errors": null,
        "extensions": null
    }