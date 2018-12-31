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

Login with username: `admin` password: `letmein`

Then view the playground at http://localhost:8080/graphql
