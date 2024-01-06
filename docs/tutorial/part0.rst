Installation and Setup
======================

.. note::

    To follow along with this tutorial you'll need a few things:

    * Python 3.8+
    * Node 18+ (hint use nvm)
    * (Optional) GNU Make

Checkout the Code
-----------------

The easiest way to follow along is to checkout the `Cannula` repo and open up
the `examples/tutorial` folders. We have the code for each section as we add
complexity to the application. You'll want to start at `part0` and move back
and forth as needed until you have mastered GraphQL::

    git clone git@github.com:rmyers/cannula.git
    cd cannula/examples/tutorial/part0

We like `GNU Make` and use `Makefiles` for all our projects as it simplifies
setup especially for beginners. In this folder you'll find a `Makefile` that
has `setup` and `help` target. If you are on a Mac you'll need to install
the xcode command line tools::

    xcode-select --install

For everyone else (hopefully) you just need to run the command::

    make setup

Create the initial application
------------------------------

We'll call our application `dashboard` since we are not creative. This will just
need the following stucture::

    dashboard/
       __init__.py
       __main__.py    # This is for running the application with `-m`
       app.py         # The FastAPI application


Makefile Reference
------------------

.. literalinclude:: ../examples/tutorial/part0/Makefile