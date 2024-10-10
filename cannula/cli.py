"""
# Run some stuff
==============

Like a boss
"""

import argparse
import importlib
import logging
import pathlib
import sys

import tomli

import cannula
from cannula.scalars import ScalarInterface

# create the top-level parser for global options
parser = argparse.ArgumentParser(
    prog="cannula",
    description="Cannula cli for general functions",
)
parser.add_argument(
    "--config",
    "-c",
    help="default configuration file (pyproject.toml)",
    default="pyproject.toml",
)
parser.add_argument(
    "--dry_run",
    "--dry-run",
    action="store_true",
    help="do not preform actions",
)
parser.add_argument(
    "--debug",
    "-d",
    action="store_true",
    help="print debug information",
)

# Sub Commands parser
subparsers = parser.add_subparsers(help="sub-command --help", dest="command")  # type: ignore

# create the parser for the "codegen" command
codegen_parser = subparsers.add_parser(
    "codegen",
    help="generate code from the schema",
)
codegen_parser.add_argument(
    "--schema",
    help="location of graphql file or directory of files",
    default=".",
)
codegen_parser.add_argument(
    "--dest",
    help="destination to write the file to",
    default="_generated.py",
)
codegen_parser.add_argument(
    "--scalar", help="custom scalar to add", type=str, action="append", dest="scalars"
)


def load_config(config) -> dict:
    source = pathlib.Path(config)
    if not source.is_file():
        return {}

    with open(source, "rb") as conf_file:
        options = tomli.load(conf_file)
        return options.get("tool", {}).get("cannula", {})


def resolve_scalars(scalars: list[str]) -> list[ScalarInterface]:
    _scalars: list[ScalarInterface] = []
    for scalar in scalars or []:
        _mod, _, _klass = scalar.rpartition(".")
        if not _mod:
            raise AttributeError(
                f"Scalar: {scalar} invalid must be a module path for import like 'my.module.Klass'"
            )
        _parent = importlib.import_module(_mod)
        _klass_obj = getattr(_parent, _klass)
        _scalars.append(_klass_obj)

    return _scalars


def run_codegen(dry_run: bool, schema: str, dest: str, scalars: list[str] | None):
    source = pathlib.Path(schema)
    documents = cannula.load_schema(source)
    destination = pathlib.Path(dest)
    _scalars = resolve_scalars(scalars or [])
    cannula.render_file(
        type_defs=documents,
        path=destination,
        dry_run=dry_run,
        scalars=_scalars,
    )


def main():
    argv = sys.argv[1:] or ["--help"]
    while argv:
        options, argv = parser.parse_known_args(argv)
        if not options.command:
            break

        level = logging.DEBUG if options.debug else logging.INFO
        sys.tracebacklimit = 99 if options.debug else -1
        logging.basicConfig(level=level)
        configuration = load_config(options.config)

        if options.command == "codegen":
            codegen_config = configuration.get("codegen", {})
            schema = codegen_config.get("schema", options.schema)
            dest = codegen_config.get("dest", options.dest)
            scalars = codegen_config.get("scalars", options.scalars)
            run_codegen(
                dry_run=options.dry_run,
                schema=schema,
                dest=dest,
                scalars=scalars,
            )
