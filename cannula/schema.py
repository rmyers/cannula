"""
Schema Utilities
----------------
"""

import logging
import pathlib
import typing
import itertools

from graphql import (
    GraphQLScalarType,
    GraphQLSchema,
    DocumentNode,
    TypeDefinitionNode,
    build_ast_schema,
    concat_ast,
    extend_schema,
    is_scalar_type,
    is_type_definition_node,
    is_type_extension_node,
    is_type_system_extension_node,
    parse,
)

from cannula.scalars import ScalarInterface

LOG = logging.getLogger(__name__)
QUERY_TYPE = parse("type Query { _empty: String }")
MUTATION_TYPE = parse("type Mutation { _empty: String }")
COMPUTED_DIRECTIVE = parse("directive @computed(weight: Int = 1) on FIELD_DEFINITION")

_TYPES = {
    "Boolean": "bool",
    "Float": "float",
    "ID": "str",
    "Int": "int",
    "String": "str",
}


def extract_extensions(ast: DocumentNode) -> DocumentNode:
    type_extensions = filter(is_type_extension_node, ast.definitions)
    system_extensions = filter(is_type_system_extension_node, ast.definitions)
    extensions = itertools.chain(type_extensions, system_extensions)
    return DocumentNode(definitions=list(extensions))


def assert_has_query_and_mutation(ast: DocumentNode) -> DocumentNode:
    """Assert that schema has query and mutation types defined.

    The schema is pretty much useless without them and rather than causing
    an error we'll just add in an empty one so they can be extended.
    """
    object_kinds: typing.List[TypeDefinitionNode] = filter(
        is_type_definition_node, ast.definitions
    )  # type: ignore
    object_definitions = [node.name.value for node in object_kinds]
    has_mutation_definition = "Mutation" in object_definitions
    has_query_definition = "Query" in object_definitions

    if not has_mutation_definition:
        LOG.debug("Adding default empty Mutation type")
        ast = concat_ast([ast, MUTATION_TYPE])

    if not has_query_definition:
        LOG.debug("Adding default empty Query type")
        ast = concat_ast([ast, QUERY_TYPE])

    LOG.debug("Adding computed directive")
    ast = concat_ast([ast, COMPUTED_DIRECTIVE])

    return ast


def maybe_parse(type_def: typing.Union[str, DocumentNode]):
    if isinstance(type_def, str):
        return parse(type_def)
    return type_def


def concat_documents(
    type_defs: typing.Iterable[typing.Union[str, DocumentNode]],
) -> DocumentNode:
    document_list = [maybe_parse(type_def) for type_def in type_defs]

    return concat_ast(document_list)


def build_and_extend_schema(
    type_defs: typing.Iterable[typing.Union[str, DocumentNode]],
    scalars: typing.Optional[typing.List[ScalarInterface]] = None,
    extensions: typing.Optional[typing.Dict[str, typing.Any]] = None,
) -> GraphQLSchema:
    """
    Build and Extend Schema

    When splitting schema into multiple files it is helpful to be able to
    extend an existing type. This is most commonly done with the `Query`
    and `Mutation` types.

    For example in one schema file you add a `Query` type::

        type Book {
            name: String
        }

        type Query {
            books: [Books]
        }

    Now in another schema file you can extend the `Query`::

        type Movie {
            name: String
        }

        extend type Query {
            movies: [Movie]
        }

    :param type_defs: list of schema or document nodes
    """
    ast_document = concat_documents(type_defs)

    ast_document = assert_has_query_and_mutation(ast_document)

    schema = build_ast_schema(ast_document)

    extension_ast = extract_extensions(ast_document)

    if extension_ast.definitions:
        LOG.debug("Extending schema")
        schema = extend_schema(
            schema, extension_ast, assume_valid=True, assume_valid_sdl=True
        )

    if extensions:
        schema.extensions = extensions

    scalar_map = {s.name: s for s in scalars or []}
    for name, definition in schema.type_map.items():
        if not is_scalar_type(definition):
            continue

        scalar = typing.cast(GraphQLScalarType, definition)

        _py_type = _TYPES.get(name, "Any")
        scalar.extensions["py_type"] = _py_type

        if extended_scalar := scalar_map.get(name):
            scalar.serialize = extended_scalar.serialize  # type: ignore
            scalar.parse_value = extended_scalar.parse_value  # type: ignore
            scalar.extensions = {
                "py_type": extended_scalar.input_module.klass,
            }

            if "imports" in schema.extensions:
                schema.extensions["imports"][extended_scalar.input_module.module].add(
                    extended_scalar.input_module.klass
                )
                schema.extensions["imports"][extended_scalar.output_module.module].add(
                    extended_scalar.output_module.klass
                )

    return schema


def load_schema(
    directory: typing.Union[str, pathlib.Path]
) -> typing.List[DocumentNode]:
    """
    Load Schema

    This utility will load schema from a directory or a single pathlib.Path

    :param directory: Directory to load schema files from
    """
    if isinstance(directory, str):
        LOG.debug(f"Converting str {directory} to path object")
        directory = pathlib.Path(directory)

    if directory.is_file():
        LOG.debug(f"loading schema from file: {directory}")
        with open(directory.absolute()) as graphfile:
            return [parse(graphfile.read())]

    def find_graphql_files():
        LOG.debug(f"Checking for graphql files to load in: '{directory}'")
        for graph in directory.glob("**/*.graphql"):
            LOG.debug(f"loading discovered file: {graph}")
            with open(graph) as graphfile:
                yield graphfile.read()

    return [parse(schema) for schema in find_graphql_files()]
