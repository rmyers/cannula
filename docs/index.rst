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

Requirements:

* Python 3.8+
* `graphql-core <https://graphql-core-3.readthedocs.io/en/latest/>`_

Use pip::

    $ pip3 install cannula

Quick Start
-----------

Here is a small `hello world` example:

.. literalinclude:: examples/hello.py

Dataloaders
-----------

TODO: example dataloader

Testing Your Code
-----------------

Since GraphQL is typed it is trivial to mock the responses to any Query or
Mutation. Cannula provides a :ref:`mock-middleware` which can mock all
types or only select few to provide flexibility when writing your tests.
Here is a small example:

.. literalinclude:: examples/mocks.py

Read More About It
------------------

.. toctree::
   :maxdepth: 2

   schema
   middleware

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
