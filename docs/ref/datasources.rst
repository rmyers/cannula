Datasources
===========

Dataloaders help avoid the N+1 error. They also help with caching and reducing boilerplate.
Here is an example using the :ref:`httpdatasource` which can be used to query a remote http resource:

.. literalinclude:: ../examples/datasources/http.py

The output looks like this::

    DEBUG:cannula.schema:loading schema from file: /home/rmyers/workspace/cannula/examples/datasources/schema.graphql
    DEBUG:cannula.schema:Adding default empty Mutation type
    DEBUG:cannula.schema:Adding computed directive
    DEBUG:asyncio:Using selector: EpollSelector
    DEBUG:cannula.datasource.http:cache set for GET 'http://localhost/users/1'
    DEBUG:cannula.datasource.http:cache found for GET 'http://localhost/users/1'
    INFO:httpx:HTTP Request: GET http://localhost/users/1 "HTTP/1.1 200 OK"
    DEBUG:cannula.datasource.http:cache set for GET 'http://localhost/users/1/widgets'
    DEBUG:cannula.datasource.http:cache found for GET 'http://localhost/users/1/widgets'
    INFO:httpx:HTTP Request: GET http://localhost/users/1/widgets "HTTP/1.1 200 OK"
    ExecutionResult(data={
        'user': {'widgets': [{'name': 'Hammer'}, {'name': 'Drill'}, {'name': 'Nail'}]},
        'another': {'widgets': [{'name': 'Hammer'}, {'name': 'Drill'}, {'name': 'Nail'}]}
    }, errors=None)


Notice the second request is cached since the datasource already resovled it.
This cache is only stored for single GraphQL request. If you want to persist
that for longer you'll need to implement that yourself.

.. automodule:: cannula.datasource.orm
    :members:
    :member-order: bysource

.. automodule:: cannula.datasource.http
    :members:
    :member-order: bysource