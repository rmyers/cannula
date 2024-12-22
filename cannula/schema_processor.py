'''
Schema Processor
================

Process a GraphQL schema DocumentNode and extract metadata.
Returns a SchemaMetadata object containing type and field metadata.

Supports metadata in the following formats:

1. YAML metadata (must be preceded by ---)::

    """
    Description text

    ---
    metadata:
        cached: true
        ttl: 3600
    """

2. Inline field metadata (single line only)::

    type Test {
        "@metadata(computed: true)"
        field: String
    }
'''

import yaml
from dataclasses import dataclass, field
from typing import Dict, Any

from graphql import DocumentNode, visit, Visitor

from cannula.utils import parse_metadata_to_yaml


@dataclass
class SchemaMetadata:
    """Container for schema metadata"""

    type_metadata: Dict[str, Any] = field(default_factory=dict)
    field_metadata: Dict[str, Dict[str, Any]] = field(default_factory=dict)


class SchemaProcessor:
    def __init__(self):
        self.type_metadata = {}
        self.field_metadata = {}

    def process_schema(self, document: DocumentNode) -> SchemaMetadata:
        '''
        Process a GraphQL schema DocumentNode and extract metadata.
        Returns a SchemaMetadata object containing type and field metadata.

        Supports metadata in the following formats:

        1. YAML metadata (must be preceded by ---):
        """
        Description text

        ---
        metadata:
          cached: true
          ttl: 3600
        """

        2. Inline field metadata (single line only):
        type Test {
            "@metadata(computed: true)"
            field: String
        }
        '''
        visitor = SchemaVisitor(self)
        visit(document, visitor)
        return SchemaMetadata(
            type_metadata=self.type_metadata,
            field_metadata=self.field_metadata,
        )

    def _extract_metadata(self, description: str) -> tuple[Dict[str, Any], str]:
        """
        Extract metadata and clean description from a documentation string.
        Returns (metadata_dict, clean_description)
        """
        # Handle inline description with @metadata marker
        description = parse_metadata_to_yaml(description)

        # Look for YAML metadata section with separator
        parts = description.split("\n---\n", 1)
        if len(parts) == 2:
            desc, yaml_str = parts
            try:
                data = yaml.safe_load(yaml_str)
                if isinstance(data, dict) and "metadata" in data:
                    return data["metadata"], desc.strip()
            except yaml.YAMLError:
                return {}, description.strip()

        return {}, description.strip()

    def _merge_metadata(
        self, existing: Dict[str, Any], new: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge new metadata with existing metadata, updating values"""
        merged = existing.copy()
        merged["metadata"].update(new["metadata"])
        return merged


class SchemaVisitor(Visitor):
    def __init__(self, processor: SchemaProcessor):
        self.processor = processor
        super().__init__()

    def _process_node(self, node):
        """Helper method to process nodes with descriptions"""
        if hasattr(node, "description") and node.description:
            return self.processor._extract_metadata(node.description.value)
        return {}, ""

    def enter_object_type_definition(self, node, *args):
        metadata, clean_desc = self._process_node(node)
        type_name = node.name.value
        self.processor.type_metadata[type_name] = {
            "metadata": metadata,
            "description": clean_desc,
        }

    def enter_object_type_extension(self, node, *args):
        metadata, clean_desc = self._process_node(node)
        type_name = node.name.value

        # If the type exists, merge the metadata
        if type_name in self.processor.type_metadata:
            self.processor.type_metadata[type_name] = self.processor._merge_metadata(
                self.processor.type_metadata[type_name],
                {"metadata": metadata, "description": clean_desc},
            )
        else:
            # Create new type metadata if it doesn't exist
            self.processor.type_metadata[type_name] = {
                "metadata": metadata,
                "description": clean_desc,
            }

    def enter_field_definition(self, node, key, parent, path, ancestors):
        metadata, clean_desc = self._process_node(node)

        parent_type = None
        for ancestor in reversed(ancestors):
            if hasattr(ancestor, "kind") and ancestor.kind in (
                "object_type_definition",
                "interface_type_definition",
                "object_type_extension",  # Also process fields from type extensions
            ):
                parent_type = ancestor.name.value
                break

        if parent_type:
            field_name = node.name.value
            if parent_type not in self.processor.field_metadata:
                self.processor.field_metadata[parent_type] = {}

            new_field_data = {"metadata": metadata, "description": clean_desc}
            self.processor.field_metadata[parent_type][field_name] = new_field_data
