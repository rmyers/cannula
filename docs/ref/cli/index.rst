CLI
===

Cannula provides a handful of powerful tools to assist you in maintence of your
GraphQL API. Using the schema to generate your files will allow you to make a
single change propogate to the rest of the system keeping things in sync.

The main entrypoint is the `cannula` command which has a number of sub commands
that you can run.


Cannula CLI
-----------

.. argparse::
   :ref: cannula.cli.parser
   :prog: cannula
   :nosubcommands:


Codegen Command
---------------

Auto generate python dataclasses and models with the :doc:`codegen-command`


Reference
+++++++++

.. toctree::
    :maxdepth: 1
    :caption: Available Commands

    codegen-command