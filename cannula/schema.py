from typing import List, Union

from graphql import (
    GraphQLSchema,
    DocumentNode,
    parse,
    build_ast_schema,
    extend_schema,
    concat_ast,
)


object_extension_kind = 'object_type_extension'
interface_extension_kind = 'interface_type_extension'
input_object_extension_kind = 'input_object_type_extension'
union_extension_kind = 'union_type_extension'
enum_extension_kind = 'enum_type_extension'

extension_kinds = [
    object_extension_kind,
    interface_extension_kind,
    input_object_extension_kind,
    union_extension_kind,
    enum_extension_kind,
]


def extract_extensions(ast: DocumentNode) -> DocumentNode:
    extensions = [node for node in ast.definitions if node.kind in extension_kinds]

    return DocumentNode(definitions=extensions)


def maybe_parse(type_def: Union[str, DocumentNode]):
    if isinstance(type_def, str):
        return parse(type_def)
    return type_def


def build_and_extend_schema(
    type_defs: Union[str, List[str]],
) -> GraphQLSchema:
    if not isinstance(type_defs, list):
        type_defs = [type_defs]

    document_list = [maybe_parse(type_def) for type_def in type_defs]

    ast_document = concat_ast(document_list)

    schema = build_ast_schema(ast_document)

    extension_ast = extract_extensions(ast_document)

    if extension_ast.definitions:
        schema = extend_schema(schema, extension_ast)

    return schema
