"""
Schema Processor
================

Process a GraphQL schema DocumentNode and extract metadata directives.
Returns a SchemaMetadata object containing type and field metadata.

Example schema::

    type User @db_sql(table_name: "workers") {
        id: ID! @field_meta(primary_key: true)
        related: [Post] @field_meta(where: "author_id = :id", args=["id"])
    }
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, Any

from graphql import (
    ArgumentNode,
    DirectiveNode,
    DocumentNode,
    SchemaDefinitionNode,
    Visitor,
    visit,
    value_from_ast_untyped,
)

from cannula.utils import pluralize
from cannula.types import (
    Argument,
    ConnectDirective,
    Directive,
    FieldMetadata,
    SQLMetadata,
    SourceDirective,
)

LOG = logging.getLogger(__name__)


@dataclass
class SchemaMetadata:
    """Container for schema metadata"""

    type_metadata: Dict[str, Any] = field(default_factory=dict)
    field_metadata: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    sources: set[SourceDirective] = field(default_factory=set)
    connectors: defaultdict[str, list[ConnectDirective]] = field(
        default_factory=defaultdict
    )


class SchemaProcessor:
    def __init__(self):
        self.type_metadata = {}
        self.field_metadata = {}
        self.sources = set()
        self.connectors = defaultdict(list)

    def process_schema(self, document: DocumentNode) -> SchemaMetadata:
        """
        Process a GraphQL schema DocumentNode and extract metadata directive.
        Returns a SchemaMetadata object containing type and field metadata.

        Example schema::

            type User @db_sql {
                id: ID! @field_meta(primary_key: true)
            }
        """
        visitor = SchemaVisitor(self)
        visit(document, visitor)
        return SchemaMetadata(
            type_metadata=self.type_metadata,
            field_metadata=self.field_metadata,
            sources=self.sources,
            connectors=self.connectors,
        )


class SchemaVisitor(Visitor):
    def __init__(self, processor: SchemaProcessor):
        self.processor = processor
        super().__init__()

    def _parse_argument(self, arg: ArgumentNode) -> Argument:
        """Parse an argument from a directive"""
        return Argument(
            name=arg.name.value,
            value=value_from_ast_untyped(arg.value) if arg.value else None,
        )

    def _parse_directive(self, directive: DirectiveNode) -> Directive:
        """Parse a directive node into a Directive type"""
        args = [self._parse_argument(arg) for arg in (directive.arguments or [])]
        return Directive(name=directive.name.value, args=args)

    def enter_schema_extension(self, schema: SchemaDefinitionNode, *args):
        directives = [self._parse_directive(d) for d in (schema.directives or [])]
        for directive in directives:
            if directive.name == "source":
                source_directive = SourceDirective(**directive.to_dict())
                self.processor.sources.add(source_directive)

    def enter_object_type_definition(self, node, *args) -> None:
        type_name = node.name.value
        meta = {}
        directives = [self._parse_directive(d) for d in (node.directives or [])]
        for directive in directives:
            if directive.name == "db_sql":
                # by default use the pluralized name as the table name
                kwargs = {"table_name": pluralize(type_name), **directive.to_dict()}
                meta["sql_metadata"] = SQLMetadata(**kwargs)

        self.processor.type_metadata[type_name] = meta

    def enter_object_type_extension(self, node, *args) -> None:
        type_name = node.name.value

        directives = [self._parse_directive(d) for d in (node.directives or [])]

        # If the type exists, merge the metadata
        if type_name in self.processor.type_metadata:
            pass
        else:
            # Create new type metadata if it doesn't exist
            self.processor.type_metadata[type_name] = {
                "directives": directives,
            }

    def enter_input_value_definition(self, node, key, parent, path, ancestors) -> None:
        parent_type = None
        for ancestor in reversed(ancestors):
            if hasattr(ancestor, "kind") and ancestor.kind in (
                "object_type_definition",
                "interface_type_definition",
                "input_object_type_definition",
                "object_type_extension",  # Also process fields from type extensions
            ):
                parent_type = ancestor.name.value
                break
        if parent_type:
            field_name = node.name.value
            if parent_type not in self.processor.field_metadata:
                self.processor.field_metadata[parent_type] = {}

            meta = {}

            # Parse directives into our custom type
            directives = [self._parse_directive(d) for d in (node.directives or [])]
            meta["directives"] = directives
            self.processor.field_metadata[parent_type][field_name] = meta

    def enter_field_definition(self, node, key, parent, path, ancestors) -> None:

        parent_type = None
        for ancestor in reversed(ancestors):
            if hasattr(ancestor, "kind") and ancestor.kind in (
                "object_type_definition",
                "interface_type_definition",
                "input_object_type_definition",
                "object_type_extension",  # Also process fields from type extensions
            ):
                parent_type = ancestor.name.value
                break

        if parent_type:
            field_name = node.name.value
            if parent_type not in self.processor.field_metadata:
                self.processor.field_metadata[parent_type] = {}

            meta: Dict[str, Any] = {}

            # Parse directives into our custom type
            directives = [self._parse_directive(d) for d in (node.directives or [])]
            meta["directives"] = directives
            for directive in directives:
                # Our field_meta directive stores database related info
                if directive.name == "field_meta":
                    meta["field_meta"] = FieldMetadata(**directive.to_dict())

                # The connect directive maps fields to http datasources
                if directive.name == "connect":
                    connector = ConnectDirective(
                        field=field_name,
                        parent=parent_type,
                        **directive.to_dict(),
                    )
                    meta["connector"] = connector
                    self.processor.connectors[connector.datasource_name].append(
                        connector
                    )

            self.processor.field_metadata[parent_type][field_name] = meta
