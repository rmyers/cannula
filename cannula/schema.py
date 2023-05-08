import logging
import os
import pathlib
import typing
import itertools

from graphql import (
    GraphQLSchema,
    GraphQLUnionType,
    DocumentNode,
    parse,
    build_ast_schema,
    extend_schema,
    concat_ast,
    is_type_extension_node,
    is_type_system_extension_node,
    is_type_definition_node,
)

LOG = logging.getLogger(__name__)
QUERY_TYPE = parse("type Query { _empty: String }")
MUTATION_TYPE = parse("type Mutation { _empty: String }")


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
    object_kinds = filter(is_type_definition_node, ast.definitions)
    object_definitions = [node.name.value for node in object_kinds]
    has_mutation_definition = "Mutation" in object_definitions
    has_query_definition = "Query" in object_definitions

    if not has_mutation_definition:
        LOG.debug("Adding default empty Mutation type")
        ast = concat_ast([ast, MUTATION_TYPE])

    if not has_query_definition:
        LOG.debug("Adding default empty Query type")
        ast = concat_ast([ast, QUERY_TYPE])

    return ast


def maybe_parse(type_def: typing.Union[str, DocumentNode]):
    if isinstance(type_def, str):
        return parse(type_def)
    return type_def


def build_and_extend_schema(
    type_defs: typing.Union[
        typing.List[str],
        typing.List[DocumentNode],
        typing.Iterator[DocumentNode],
    ],
) -> GraphQLSchema:
    document_list = [maybe_parse(type_def) for type_def in type_defs]

    ast_document = concat_ast(document_list)

    ast_document = assert_has_query_and_mutation(ast_document)

    schema = build_ast_schema(ast_document)

    extension_ast = extract_extensions(ast_document)

    if extension_ast.definitions:
        LOG.debug("Extending schema")
        schema = extend_schema(
            schema, extension_ast, assume_valid=True, assume_valid_sdl=True
        )

    return schema


def fix_abstract_resolve_type(schema: GraphQLSchema) -> GraphQLSchema:
    # We need to provide a custom 'resolve_type' since the default
    # in method only checks for __typename if the source is a dict.
    # Python mangles the variable name if it starts with `__` so we add
    # `__typename__` attribute which is not mangled.
    # TODO(rmyers): submit PR to fix upstream?

    def custom_resolve_type(source, _info):
        if isinstance(source, dict):
            return str(source.get("__typename"))
        return getattr(source, "__typename__", None)

    for _type_name, graphql_type in schema.type_map.items():
        if isinstance(graphql_type, GraphQLUnionType):
            graphql_type.resolve_type = custom_resolve_type

    return schema


def load_schema(directory: str) -> typing.List[DocumentNode]:
    assert os.path.isdir(directory), f"Directory not found: {directory}"
    path = pathlib.Path(directory)

    def find_graphql_files():
        for graph in path.glob("**/*.graphql"):
            with open(os.path.join(directory, graph)) as graphfile:
                yield graphfile.read()

    return [parse(schema) for schema in find_graphql_files()]
