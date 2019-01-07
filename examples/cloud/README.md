Openstack Private Cloud
-----------------------

This is an full example of using GraphQL and Cannula on a mock Openstack
private cloud instance. Openstack is sufficiently complicated to show off the
power of Cannula to simplify your UI with GraphQL.

This example shows interaction with 4 different apis:
* Keystone (identity)
* Neutron (networks)
* Nova (compute)
* Cinder (block storage)

You *might* be able to point this at a real Openstack cloud :shrug:

Quick Start
-----------

You can start the mock cloud with docker-compose like:

```bash
$ docker-compose up
```

Or use the make:
```
$ make up
```

View the mock site at http://localhost:8080/

Login with any username or password that you like. If you use use `admin` or
`readonly` as the username the UI will unlock or lock features accordingly.

Then view the playground at http://localhost:8080/graphql

Application Details
-------------------

This example application uses [bottle](https://bottlepy.org/docs/dev/) because
it is small and simple enough that it does not get in the way of our example
application logic. You can use any framework, or none at all, and get the
same results.

Here is the project layout:

```
app.py                    # API and Views for the application (bottle).
session.py                # Simple in memory session.
mock_server.py            # Our mock API's mimics the services we use.
resolvers/                # The custom resolvers for our application.
    base.py               # Base OpenStack API resolver.
    compute/              # Schema and resolvers for the `compute` API.
    identity/             # Schema and resolvers for the `identity` API.
    network/              # Schema and resolvers for the `network` API.
    storage/              # Schema and resolvers for the `block storage` API.
static/                   # Javascript and CSS for the site.
views/                    # Templates for bottle views.
```
