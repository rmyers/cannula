Resolvers
=========

Resolvers define how to fetch the data defined in your schema. There are many
ways to access your data but resolvers are just a simple async function that
return either an object or a dictionary that matches the shape of the Schema
return type.

This could be the raw json response from a third party library or it could be
a database model that represents your data. The great thing about resolvers
are they are completely flexible as long as the type you are returning is correct.
Which means you can combine loosly related items into a single parent.

.. toctree::
   :maxdepth: 2

.. automodule:: cannula.api
   :members: