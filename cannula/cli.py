import argparse
import logging
import pathlib
import sys

import tomli

import cannula
from cannula.codegen import render_file
from cannula.utils import resolve_scalars

# create the top-level parser for global options
parser = argparse.ArgumentParser(
    prog="cannula",
    description="Cannula command for performing code generation and migrations.",
)
parser.add_argument(
    "--config",
    help="Specify a different location or name of the configuration file. This should be a well formatted TOML file.",
    default="pyproject.toml",
)


# Sub Commands parser
subparsers = parser.add_subparsers(dest="command")  # type: ignore

# create the parser for the "codegen" command
codegen_parser = subparsers.add_parser(
    "codegen",
    help="Generate Python objects from GraphQL schema files.",
)
codegen_parser.add_argument(
    "--dry_run",
    "--dry-run",
    action="store_true",
    help="Do not write any changes to the file instead print output to terminal",
)
codegen_parser.add_argument(
    "--debug",
    "-d",
    action="store_true",
    help="Display debug information while parsing and generating code.",
)
codegen_parser.add_argument(
    "--schema",
    help="Specify a path or location for the schema files to use.",
    default=".",
)
codegen_parser.add_argument(
    "--dest",
    help="Change the default location of the output folder.",
    default="gql",
)
codegen_parser.add_argument(
    "--operations",
    help="Specify a path or location for the operations to generate.",
    default="operations.graphql",
)
codegen_parser.add_argument(
    "--app-directory",
    "--app_directory",
    help="Change the default location of the application folder.",
    default="app",
)
codegen_parser.add_argument(
    "--operations-directory",
    "--operations_directory",
    help="Change the default location of the operations folder.",
    default=None,
)
codegen_parser.add_argument(
    "--force",
    "-f",
    action="store_true",
    help="Force overwriting existing operations templates.",
)
codegen_parser.add_argument(
    "--scalar",
    help="Scalars to use during code generation, this can be specified multiple times.",
    type=str,
    action="append",
    dest="scalars",
)
codegen_parser.add_argument(
    "--use-pydantic",
    "--use_pydantic",
    action="store_true",
    help="Use Pydantic models for generated classes.",
)


def load_config(config) -> dict:
    source = pathlib.Path(config)
    if not source.is_file():
        return {}

    with open(source, "rb") as conf_file:
        options = tomli.load(conf_file)
        return options.get("tool", {}).get("cannula", {})


def run_codegen(
    dry_run: bool,
    schema: str,
    dest: str,
    scalars: list[str] | None,
    use_pydantic: bool,
    operations: str,
    operations_dir: pathlib.Path,
    force: bool,
):
    source = pathlib.Path(schema)
    documents = cannula.load_schema(source)
    destination = pathlib.Path(dest)
    _scalars = resolve_scalars(scalars or [])
    render_file(
        type_defs=documents,
        dest=destination,
        dry_run=dry_run,
        scalars=_scalars,
        use_pydantic=use_pydantic,
        operations=operations,
        operations_dir=operations_dir,
        force=force,
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
            use_pydantic = codegen_config.get("use_pydantic", options.use_pydantic)
            operations = codegen_config.get("operations", options.operations)
            app_dir = codegen_config.get("app_directory", options.app_directory)
            operations_dir = codegen_config.get(
                "operations_directory", options.operations_directory
            )
            if operations_dir is None:
                operations_dir = pathlib.Path(app_dir) / "_operations"
            run_codegen(
                dry_run=options.dry_run,
                schema=schema,
                dest=dest,
                scalars=scalars,
                use_pydantic=use_pydantic,
                operations=operations,
                operations_dir=operations_dir,
                force=options.force,
            )
