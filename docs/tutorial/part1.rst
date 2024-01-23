Part1: Schema
=============

Cannuala uses a schema first design which means we need to think about the data
we wish to expose in our service. We could just do a one to one relation with our
data models in the database. In practice that is not very useful for the UI
except for very simple TODO applications. In this tutorial we will try to model
a more realalistic application.

First let's describe what we want in this application. Our application will be
a dashboard with two main personas a User and an Admin.
The users will see a snapshot of the items that they have created along with
quota's of the remaining resources. Then they will have links to detail pages
where they can view the full list of a particular item and perform CRUD actions.
Admins will get an overall view of the resources created by all users and
view the resource pages for all users to perform CRUD actions.

The data types we will need to acomplish this are:

* Users/Admins
* Resources
* Quota
* Charts/Graphs

Since we have two personas we can describe them as an interface `Persona` this
will allow us to have difference types in the future. Even though these are all
saved in a single database table. This will allow us to treat these individuals
differently in the graph resolution

.. code-block:: graphql
    :emphasize-lines: 2,3,4

    interface Persona {
        id: ID!
        name: String
        email: String
    }

    type User implements Persona {
        id: ID!
        name: String
        email: String
        quota: [Quota]
    }

    type Admin implements Persona {
        id: ID!
        name: String
        email: String
    }

.. note:: A `type` that implement an `interface` need to include the fields from the `interface`.

There are a handful of default `scalar` types that are included. Those are:

* `ID`: Represents an `id` field from a database, it is parsed as a 'string'.
* `Int`: Represents an integer.
* `String`: Represents a string.
* `Boolean`: Represents a boolean.
* `Float`: Represents a float.

By default all the fields are optional, you can mark them as 'required' by adding an `!` at the
end. That will mark the queries that request this data fail if it is not present. Be careful
setting this in your schema as it makes it less flexible in the future. The one place that it is
useful for is `input` types which we will go over later.

You can represent a list of types by placing it in brackets like::

    list_of_custom_types: [Quota]
    list_of_default_scalars: [String]

As you may have noticed we included `Quota` in the `User` type, but we didn't define it yet. In the
schema the order of items doesn't matter as long as it is in the schema somewhere. So we can include
this new type before or after the `User`. You can even inlude a type within itself for self referencing
fields. We could have a `manager: User` for example. Our `Quota` and `Resource` are cross related
where we can have multiple `Resource` types that each have a `Quota` and users have multiple `Quota`
objects that are tied to a single `Resource`. It is all very confusing, but hopefully we can describe
this relationship in the schema.

Our `Resource` can be anything that has a `Quota` attached to it. For this application we'll start
out with just two, a `Board`, and a `Post`. We are going to limit our users to a fixed amount of
these items so each will have a separate `Quota` in our system.

.. code-block:: graphql

    type Quota {
        user: User
        resource: Resource
        limit: Int
        count: Int
    }

    interface Resource {
        quota: Quota
        user: User
        created: String
    }

    type Board implements Resource {
        id: ID
        quota: Quota
        user: User
        title: String
        created: String
        posts: [Post]
    }

    type Post implements Resource {
        id: ID
        quota: Quota
        user: User
        title: String
        created: String
        body: String
    }

Great we have some basic types defined and we have the relations of them. Now we just need
some ways to interact with these types. To do that we must define special `Operation` types:
`Query`, `Mutation`, and `Subscription`. Technically under the hood there is no real difference
between these operations, but clients treat them differently. A `Query` is a read operation that
can happen in parallel and could be cached. A `Mutation` alters data in some way and should never
be cached and should be done in a tranaction like way, ie serialy. `Subscription` is a special
`Query` that is a stream of data, we'll save this one for the advanced parts.

Our users can do CRUD operations on `Board` and `Post` types. And the UI will need to be able to
show the User/Admin details, so we'll need a few `Query` and a couple `Mutation` items. Since
in the schema these are object types they have fields and return types just like our custom types.
However they also may have arguments. This looks a little like a function definition:

.. code-block:: graphql

    field(arg: Type, ..., argN: Type): Type

Here is our `Query` and `Mutation` types:

.. code-block:: graphql

    type Query {
        me: Persona
        user(id: ID): User
        boards(limit: Int = 100, offset: Int = 0): [Board]
        posts(limit: Int = 100, offset: Int = 0): [Post]
    }

    type Mutation {
        createPost(title: String!, body: String!): Post
        deletePost(id: ID!): Boolean
        editPost(id: ID!, title: String, body: String): Post
        createBoard(title: String!): Board
        deleteBoard(id: ID!): Boolean
        editBoard(id: ID!, title: String): Board
        addPost(board_id: ID!, post_id: ID!): Board
    }

With our basic schema types defined we are ready to wire this up to our application.
Create our schema in a new folder `part1`. Add a file `schema.graphql` with the schema
defined above. We need to tell `cannula` where to find it. The easiest way is with
pathlib:

.. code-block:: python

    import pathlib

    BASE_DIR = pathlib.Path(__file__).parent
    cannula_app = cannula.API(schema=BASE_DIR / "schema.graphql")

Then we just need to create a `graph` handler in our fastapi application, we'll use
the contrib package to gather the payload from the request. In fastapi that is done
with dependency injection with the typehints:

.. code-block:: python
    :emphasize-lines: 2,7

    from fastapi import APIRouter, Request
    from cannula.contrib.asgi import GraphQLPayload

    part1 = APIRouter(prefix="/part1")

    @part1.post("/graph")
    async def graph(request: Request, payload: GraphQLPayload):
        ...

.. note:: GraphQL requests are always a "POST" request

Then from the payload pass the arguments to the `cannula_app` we created:

.. code-block:: python

    @part1.post("/graph")
    async def graph(request: Request, payload: GraphQLPayload):
        results = await cannula_app.call(
            payload.query, request, variables=payload.variables
        )
        return {"data": results.data, "errors": results.errors}

Now we just need to call this and to test it out. Typically you would do this
with a client side javascript library but we can just use the `fetch` library:

.. code-block:: javascript
    :emphasize-lines: 8-13

    {% extends 'base.html' %}
    {% block content %}
    <h1>Part One: Schema</h1>

    <script>
        async function runRequest() {
            const query = `
                query LoggedInUser {
                    me {
                        id
                        name
                    }
                }
            `;
            const body = JSON.stringify({ query });
            const resp = await fetch(
                '/part1/graph', {
                body: body,
                method: "POST",
                headers: { 'Content-Type': 'application/json' }
            });
            const output = document.getElementById('output');
            const content = await resp.text();
            output.innerHTML = content;
        }
    </script>
    <button onclick="runRequest()">Run Request</button>
    <h2>Results:</h2>
    <pre id="output"></pre>
    {% endblock %}


You can see the full output at http://localhost:8000/part1/ click the
'Run Request' button you'll see that we don't get any errors. YAY! but we don't
get any data either:

.. code-block:: javascript

    {"data":{"me":null},"errors":null}

Head on over to part 2 to add resolvers to our application.