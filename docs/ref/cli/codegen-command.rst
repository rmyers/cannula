Codegen Command
===============

Generate Python dataclasses or Pydantic models to represent your schema files. This
command will overwrite any existing file so pay attention to the destination path
and refrain from making edits to the generated file as they will be lost.

Configuration
-------------

You can use the command line to specify all the settings, however it is much easier to
add this to your `pyproject.toml` file like so:

.. literalinclude:: ../../examples/codegen/pyproject.toml

If you prefer to place it in a different file you can then override that on the command
line when running codegen::

    $ cannula -c myconfig.toml codegen

Usage
-----

.. argparse::
    :ref: cannula.cli.parser
    :prog: cannula
    :path: codegen