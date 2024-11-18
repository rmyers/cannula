Scalars
=======

Scalars are a way to extend the schema input and output types. The basic
scalars are usually enough for most projects, however adding a few extra
types makes working with the requests and responses a little easier.

Cannula provides a handful of useful scalars which might be all you need.
You just need to specify these in you configuration and add them to your
schema. These will automatically serialize and deserialize the values
from an `Input` type or when rendering the data.

Example schema::

    scalar Datetime

    type MyModel {
       id: id
       created: Datetime
    }

Then in your :class:`cannula.api.CannulaAPI` specify the scalars you are
using with the full dotted import path::

    graph = CannulaAPI(
        PARENT_DIR / 'schema.graphql',
        scalars=[
            "cannula.scalars.date.Datetime"
        ]
    )


Built-in Scalars
----------------

.. automodule:: cannula.scalars.date
    :members:

.. automodule:: cannula.scalars.util
    :members:


Custom Scalars
--------------

If the Built-in Scalars are not quite perfect or you need something else, you
can easily define your own. Simply create a subclass of the :class:`cannula.scalars.ScalarType`
and provide a :meth:`serialize` and :meth:`parse_value` methods.

.. automodule:: cannula.scalars
   :members:

