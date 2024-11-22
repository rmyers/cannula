Part5: Datasources
==================

Datasources provide two purposes, first they reduce the number of duplicate queries made
and second reducing the amount of boilerplate we have to write. In the previous sections
we are fetching data from the database and returning our generated models. Lets look at
how dataloaders can help.

DatabaseRepository
------------------

Cannula provides a :class:`cannula.datasource.orm.DatabaseRepository` which can be used
to connect our database to our resolvers. It uses Generic types to associate the ORM model
to the Graph Model.

This may seem a little redundant but the generic types are used to ensure the type hints
are correct and the class variables for these 'concrete' objects are used to create
objects.

.. code-block:: python

    class UserRepository(
        DatabaseRepository[DBUser, User],
        db_model=DBUser,
        graph_model=User,
    ):

        async def add_user(self, name: str, email: str) -> User:
            return await self.add(name=name, email=email)

        async def get_users(self) -> list[User]:
            return await self.get_models()

    class QuotaRepository(
        DatabaseRepository[DBQuota, Quota],
        db_model=DBQuota,
        graph_model=Quota,
    ):

        async def get_quota_for_user(self, id: uuid.UUID) -> list[Quota]:
            return await self.get_models(DBQuota.user_id == id)

        async def get_over_quota(self, id: uuid.UUID, resource: str) -> Quota | None:
            return await self.get_model_by_query(
                DBQuota.user_id == id, DBQuota.resource == resource
            )

.. note::
    The :class:`cannula.datasource.orm.DatabaseRepository` requires a :func:`async_sessionmaker`
    function as the first argument which is used by the class to create a session used by
    the resolvers. Certain queries execute in parallel in different coroutines and since
    the :class:`AsyncSession` are not thread safe they cannot be shared between them.
    Which means each coroutine must use it's own session.

Setup Context
-------------

Now we need to connect our repositories to our context so that we can share the
datasources between the different resolvers. These datasource objects will cache the
queries that are safe to replay and return the same results so that we only query the
database once.

.. literalinclude:: ../examples/tutorial/dashboard/part5/context.py

.. note::
    The :class:`cannula.datasource.orm.DatabaseRepository` has an optional read only
    :func:`async_sessionmaker` as the second argument. This will be used if provided
    to preform read only queries.


Update Graph Models
-------------------

With our Context configured we can setup the computed functions to use these from
the context. Adding our datasources to the context is not only handy for access it
helps prevent circular references. As our our Graph Models are used in the datasource
definition.

.. code-block:: python

    # This is to avoid circular imports, we only need this reference for
    # checking types in like: `cannula.ResolveInfo["Context"]`
    if TYPE_CHECKING:
        from .context import Context


    class User(UserType):
        """User Graph Model"""

        async def quota(self, info: cannula.ResolveInfo["Context"]) -> list["Quota"] | None:
            return await info.context.quota_repo.get_quota_for_user(self.id)


This example shows how our `User` Graph Model can fetch the related data using
the datasources all without having hard references to the actual source.

Route changes
--------------

Our GraphQL route needs a small adjustment as well to setup the context properly:

.. literalinclude:: ../examples/tutorial/dashboard/part5/routes.py


Sample queries
--------------

Once again go to the Apollo sandbox:

https://studio.apollographql.com/sandbox/explorer/

Update the route to `http://localhost:8000/part5/graph` and run a new query. For this
we'll manufacture a duplicate query. The easiest way to do that is to just preform
the same query in a group.

.. code-block:: graphql

    query People {
        people {
            name
            quota {
                resource
            }
        }
        another: people {
            name
            quota {
                resource
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
                    "quota": [
                        {
                            "resource": "fire",
                        },
                        {
                            "resource": "water",
                        }
                    ],
                },
                {
                    "name": "Admin User",
                    "quota": [
                        {
                            "resource": "fire",
                        }
                    ],
                }
            ],
            "another": [
                {
                    "name": "Normal User",
                    "quota": [
                        {
                            "resource": "fire",
                        },
                        {
                            "resource": "water",
                        }
                    ],
                },
                {
                    "name": "Admin User",
                    "quota": [
                        {
                            "resource": "fire",
                        }
                    ],
                }
            ]
        },
        "errors": null,
        "extensions": null
    }

But you'll see in the logs we only have three queries to the database. The first one is fetching
all the users and the second and third are fetching the quota for each user. But since the
datasource has seen these in the same request the results are returned for the duplicates::

    INFO: sqlalchemy.engine.Engine BEGIN (implicit)
    INFO: sqlalchemy.engine.Engine SELECT user_account.email, user_account.name, user_account.password, user_account.is_admin, user_account.id, user_account.created
        FROM user_account
        LIMIT ? OFFSET ?
    INFO: sqlalchemy.engine.Engine [generated in 0.00022s] (100, 0)
    INFO: sqlalchemy.engine.Engine SELECT user_quota.user_id, user_quota.resource, user_quota."limit", user_quota.count, user_quota.id, user_quota.created
        FROM user_quota
        WHERE user_quota.user_id = ?
        LIMIT ? OFFSET ?
    INFO: sqlalchemy.engine.Engine [generated in 0.00023s] ('e340b6059eaa4ca696691b7c9d343dd9', 100, 0)
    INFO: sqlalchemy.engine.Engine SELECT user_quota.user_id, user_quota.resource, user_quota."limit", user_quota.count, user_quota.id, user_quota.created
        FROM user_quota
        WHERE user_quota.user_id = ?
        LIMIT ? OFFSET ?
    INFO: sqlalchemy.engine.Engine [cached since 0.0009587s ago] ('4dca2f5476fd491799f7bef3d797a74b', 100, 0)

.. note::
    You will also see `'cached since 0.0009587s ago'` this is actually sqlalchemy referring to the
    select statement itself which it will cache so the next time it does not have to generate
    the SQL again. But it does not cache any results.