Datasources
===========

Dataloaders help avoid the N+1 error. They also help with caching and reducing boilerplate.
Here is an example using the :ref:`httpdatasource` which can be used to query a remote http resource:

.. literalinclude:: ../examples/http_datasource.py

The output looks like this::

    DEBUG:cannula.schema:Adding default empty Mutation type
    DEBUG:asyncio:Using selector: EpollSelector
    DEBUG:cannula.datasource.http:cache set for GET 'http://localhost/widgets'
    DEBUG:cannula.datasource.http:cache found for GET 'http://localhost/widgets'
    INFO:httpx:HTTP Request: GET http://localhost/widgets "HTTP/1.1 200 OK"
    {
        'widgets': [{'name': 'hammer', 'type': 'tool'}],
        'another': [{'name': 'hammer', 'type': 'tool'}]
    }

Notice the second request is cached since the datasource already resovled it.
This cache is only stored for single GraphQL request. If you want to persist
that for longer you'll need to implement that yourself.

.. automodule:: cannula.datasource.http
   :members:

.. automodule:: cannula.datasource.orm
   :members: