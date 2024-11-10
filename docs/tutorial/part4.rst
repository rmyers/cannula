Part4: Computed and Complex Fields
==================================

In many web applications not everything fits in the same data types or structures. We
usually have a relation from one thing to another and that relation can be either hard
or soft. For instance in a relational database you might have a foreign key from a
parent to their child. That would be a hard relation and it is easy to reason about
and code up. However what if your manager asked you to find all the cousins of a given
person, well that is not so simple, the data is there but your gonna have to do a bunch
of work to get the answer.

Cannula has built into the codegen logic the concept of `computed` fields. These are fields
you want to expose on the model but you don't have an easy attribute to lookup. While it
doesn't make the work of finding cousins easier, it does make it possible to do in an easy
to follow structure. We already saw this in the generated Python, all the Query and
Mutations are examples of this. To add a computed field you just need to add args to the
field or the `@computed` directive.

Here is our example schema:

.. literalinclude:: ../examples/tutorial/dashboard/part4/schema.graphql
    :emphasize-lines: 7,8

Now when we run `cannula codegen` we get this:

.. literalinclude:: ../examples/tutorial/dashboard/part4/_generated.py
    :emphasize-lines: 36,37,40,41

Our `UserTypeBase` now has the fields represented with an abstract method which we just
need to implement. The `Quota` type is a foreign key relation so it is easy to add that
in, and the nice thing is that this field is lazy. If our query doesn't ask for this
data then the relation is not queried. In sqlalchemy this is exposed via the `AsyncAttrs`

.. code-block:: python

    from sqlalchemy.ext.asyncio import AsyncAttrs
    from sqlalchemy.orm import DeclarativeBase

    class Base(AsyncAttrs, DeclarativeBase):
        pass

Here is how we can use that in our updated `models.py`:

.. literalinclude:: ../examples/tutorial/dashboard/part4/models.py
    :emphasize-lines: 18,19,20,21,22,24,25,26,27,28,29,30,31,32

The graph changes slightly because we simplied the schema:

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