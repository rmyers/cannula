"""
# Run some stuff
==============

Like a boss
"""

import argparse
import logging
import pathlib
import sys

import cannula

# create the top-level parser for global options
parser = argparse.ArgumentParser(
    prog="cannula",
    description="Cannula cli for general functions",
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
    "schema",
    help="location of graphql file or directory of files",
)
codegen_parser.add_argument(
    "--dest",
    help="destination to write the file to",
    default="_generated.py",
)


def run_codegen(dry_run: bool, schema: str, dest: str):
    source = pathlib.Path(schema)
    documents = cannula.load_schema(source)
    destination = pathlib.Path(dest)
    cannula.render_file(
        type_defs=documents,
        path=destination,
        dry_run=dry_run,
    )


def main():
    argv = sys.argv[1:] or ["--help"]
    while argv:
        options, argv = parser.parse_known_args(argv)
        if not options.command:
            break
        level = logging.DEBUG if options.debug else logging.INFO
        logging.basicConfig(level=level)
        if options.command == "codegen":
            run_codegen(
                dry_run=options.dry_run,
                schema=options.schema,
                dest=options.dest,
            )
