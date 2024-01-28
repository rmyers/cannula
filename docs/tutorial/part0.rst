Tutorial Setup
==============

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
    cd cannula/examples/tutorial

We like `GNU Make` and use `Makefiles` for all our projects as it simplifies
setup especially for beginners. In this folder you'll find a `Makefile` that
has `setup` and `help` target::

    make setup

.. note::

    If you are on MacOS you may need to install the xcode command line tools::

        xcode-select --install

This will create a virtualenv `venv` with all the dependencies we need installed:

.. literalinclude:: ../examples/tutorial/requirements.txt


Create the initial application
------------------------------

We'll call our application `dashboard` since we are not creative. This will just
need the following stucture::

    dashboard/
        core/
            app.py         # The FastAPI application
            config.py      # Configuration settings for the application
            database.py    # Database schema
        part1...n/         # Remaining sections of this tutorial
        templates/
            index.html
        __init__.py
        __main__.py        # Click commands to run tasks `python -m dashboard <command>`

We are going to use FastAPI since it is a very good ASGI application base. Since
it does not have any actual webserver process, we will need to serve the application
with uvicorn. `Jinja2` is used for the templates so there is a little bit of setup
we have to do in order to server the application.

To start up the application just run the command::

    make run

Then open your browser and visit `http://localhost:8000`:(http://localhost:8000)

For this tutorial we have setup 100% unit test coverage. We feel like it is best to show
by example, and the best developers write tests. Maintaining 100% coverage is easier if
you start with full coverage. This can then be enforced with a single line `fail_under = 100`.
What we really like about this is that it makes CI do the dirty work of scolding developers
that do not write tests. Nobody likes that person on the team who constantly nit picks PR's.
It is best for that person to be a machine, one it is less personal, and two they can't be
bribed for a +1.

For our tests we are using pytest and a few plugins, the most important one being
`pytest-asyncio`. This plugin makes it easy to write tests for our async handlers we have
this set to `auto` mode in our configuration:

.. literalinclude:: ../examples/tutorial/setup.cfg

