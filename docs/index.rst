Cannula Documentation
=====================

Using GraphQL you can simplify your web application stack and reduce
dependencies to achieve the same customer experience without regret. By using
just a few core libraries you can increase productivity and make your
application easier to maintain.

Our Philosophy:

1. Make your site easy to maintain.
2. Document your code.
3. Don't lock yourself into a framework.
4. Be happy!

Listen to me talk about `GraphQL`:

.. raw:: html

    <iframe width="560" height="315" src="https://www.youtube.com/embed/SgbZ1Qs3Vxg" frameborder="0" allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>

Installation
------------

.. note::

    Basic Requirements:

    * Python 3.8+
    * `graphql-core <https://graphql-core-3.readthedocs.io/en/latest/>`_

Using pip::

    $ pip3 install cannula

Quick Start
-----------

Here is a small `hello world` example:

.. literalinclude:: examples/hello.py

Dataloaders
-----------

Dataloaders help avoid the N+1 error. They also help with caching and reducing boilerplate.
Here is an example using the :ref:`httpdatasource` which can be used to query a remote http resource:

.. literalinclude:: examples/http_datasource.py

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

Testing Your Code
-----------------

Since GraphQL is typed it is trivial to mock the responses to any Query or
Mutation. Cannula provides a :ref:`mock-middleware` which can mock all
types or only select few to provide flexibility when writing your tests.

Read More About It
------------------

.. toctree::
   :maxdepth: 2

   schema
   resolvers
   context
   datasources
   middleware
