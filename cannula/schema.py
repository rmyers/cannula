"""
Schema Utilities
----------------
"""

import collections
import logging
import pathlib
import typing

from graphql import (
    GraphQLField,
    GraphQLInputObjectType,
    GraphQLInterfaceType,
    GraphQLObjectType,
    GraphQLScalarType,
    GraphQLSchema,
    DocumentNode,
    DirectiveDefinitionNode,
    TypeDefinitionNode,
    build_ast_schema,
    concat_ast,
    is_input_object_type,
    is_interface_type,
    is_object_type,
    is_scalar_type,
    is_type_definition_node,
    is_union_type,
    parse,
)
from typing_extensions import TypedDict

from cannula.scalars import ScalarInterface
from cannula.schema_processor import SchemaProcessor
from cannula.directives import DB_SQL, FIELD_META, CONNECT

LOG = logging.getLogger(__name__)
QUERY_TYPE = parse("type Query { _empty: String }")
MUTATION_TYPE = parse("type Mutation { _empty: String }")

Imports = typing.DefaultDict[str, set[str]]


class Extension(TypedDict):
    imports: Imports


_TYPES = {
    "Boolean": "bool",
    "Float": "float",
    "ID": "str",
    "Int": "int",
    "String": "str",
}


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

    return ast


def ensure_schema_has_directive(ast: DocumentNode) -> DocumentNode:
    """Add default directives if missing"""
    directive_definitions = [
        node.name.value
        for node in ast.definitions
        if isinstance(node, DirectiveDefinitionNode)
    ]
    has_db_sql = "db_sql" in directive_definitions
    has_field_meta = "field_meta" in directive_definitions
    has_connect = "connect" in directive_definitions

    if not has_db_sql:
        LOG.debug("Adding db_sql directive")
        ast = concat_ast([ast, DB_SQL])

    if not has_field_meta:
        LOG.debug("Adding field_meta directive")
        ast = concat_ast([ast, FIELD_META])

    if not has_connect:
        LOG.debug("Adding connect and source directives")
        ast = concat_ast([ast, CONNECT])

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
    extensions: typing.Optional[Extension] = None,
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
    ast_document = ensure_schema_has_directive(ast_document)

    processor = SchemaProcessor()
    metadata = processor.process_schema(ast_document)

    schema = build_ast_schema(ast_document)

    schema.extensions = {
        "imports": collections.defaultdict(set[str]),
        "type_metadata": metadata.type_metadata,
        "field_metadata": metadata.field_metadata,
        "sources": metadata.sources,
        "connectors": metadata.connectors,
    }

    if extensions:
        schema.extensions.update(extensions)

    # Custom scalar mapping used to apply 'serialize' and 'parse_value'
    # functions as we loop through the type map setting the Python types.
    scalar_map = {s.name: s for s in scalars or []}

    # Set the Python types for all the objects in the schema,
    # scalars should map a builtin or custom scalar type like 'datetime'.
    for name, definition in schema.type_map.items():
        is_private = name.startswith("__")

        if is_input_object_type(definition):
            definition = typing.cast(GraphQLInputObjectType, definition)
            definition.extensions["py_type"] = name
            field_meta = metadata.field_metadata.get(name, {})
            for field_name, field in definition.fields.items():
                field = typing.cast(GraphQLField, field)
                field.extensions.update(**field_meta.get(field_name, {}))

        elif is_union_type(definition):
            definition.extensions["py_type"] = name

        elif is_object_type(definition) and not is_private:
            definition = typing.cast(GraphQLObjectType, definition)
            definition.extensions["py_type"] = name
            definition.extensions["db_type"] = f"DB{name}"
            definition.extensions.update(**metadata.type_metadata[name])
            field_meta = metadata.field_metadata.get(name, {})
            for field_name, field in definition.fields.items():
                field = typing.cast(GraphQLField, field)
                field.extensions.update(**field_meta.get(field_name, {}))

        elif is_interface_type(definition):
            definition = typing.cast(GraphQLInterfaceType, definition)
            definition.extensions["py_type"] = name
            field_meta = metadata.field_metadata.get(name, {})
            for field_name, field in definition.fields.items():
                field = typing.cast(GraphQLField, field)
                field.extensions.update(**field_meta.get(field_name, {}))

        elif is_scalar_type(definition):

            scalar = typing.cast(GraphQLScalarType, definition)

            _py_type = _TYPES.get(name, "Any")
            scalar.extensions["py_type"] = _py_type

            if extended_scalar := scalar_map.get(name):
                scalar.serialize = extended_scalar.serialize  # type: ignore
                scalar.parse_value = extended_scalar.parse_value  # type: ignore
                scalar.extensions = {
                    "py_type": extended_scalar.input_module.klass,
                }

                schema.extensions["imports"][extended_scalar.input_module.module].add(
                    extended_scalar.input_module.klass
                )
                schema.extensions["imports"][extended_scalar.output_module.module].add(
                    extended_scalar.output_module.klass
                )

    return schema


def load_schema(
    directory: typing.Union[str, pathlib.Path],
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
