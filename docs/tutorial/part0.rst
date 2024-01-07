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
has `setup` and `help` target::

    make setup

.. note::

    If you are on MacOS you may need to install the xcode command line tools::

        xcode-select --install

This will create a virtualenv `venv` with all the dependencies we need installed:

.. literalinclude:: ../examples/tutorial/part0/requirements.txt


Create the initial application
------------------------------

We'll call our application `dashboard` since we are not creative. This will just
need the following stucture::

    dashboard/
       templates/
          index.html
       __init__.py
       __main__.py    # This is for running the application with `-m`
       app.py         # The FastAPI application
       config.py      # Configuration settings for the application

We are going to use FastAPI since it is a very good ASGI application base. Since
it does not have any actual webserver process, we will need to serve the application
with uvicorn. `Jinja2` is used for the templates so there is a little bit of setup
we have to do in order to server the application.

.. literalinclude:: ../examples/tutorial/part0/dashboard/app.py

To start up the application just run the command::

    make run

Then open your browser and visit