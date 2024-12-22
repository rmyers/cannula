from dataclasses import dataclass, field
from graphql import DocumentNode, visit, GraphQLError, Visitor
from typing import Dict, Any, Optional
import re


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
        Process a GraphQL schema DocumentNode and extract metadata from documentation strings.
        Returns a SchemaMetadata object containing type and field metadata.

        The processor looks for specially formatted documentation strings like:
        ```
        """
        @metadata(
            cached: true,
            ttl: 3600,
            description: "some long
                         multiline description"
        )
        Type description here
        """
        ```
        '''
        try:
            visitor = SchemaVisitor(self)
            visit(document, visitor)
            return SchemaMetadata(
                type_metadata=self.type_metadata,
                field_metadata=self.field_metadata,
            )

        except GraphQLError as e:
            raise ValueError(f"Invalid GraphQL schema: {str(e)}")

    def _extract_metadata(
        self, description: Optional[str]
    ) -> tuple[Dict[str, Any], str]:
        """
        Extract metadata and clean description from a documentation string.
        Returns (metadata_dict, clean_description)
        """
        if not description:
            return {}, ""

        # Look for @metadata(...) directive with possible multiple lines
        metadata_pattern = r"@metadata\((.*?)\)"
        match = re.search(metadata_pattern, description, re.DOTALL)

        if not match:
            return {}, description

        metadata_str = match.group(1)
        clean_desc = re.sub(
            r"@metadata\(.*?\)\s*", "", description, flags=re.DOTALL
        ).strip()

        # Parse metadata key-value pairs
        metadata = {}
        current_key = None
        current_value = []

        # Split by commas but preserve commas inside quoted strings
        lines = re.findall(r'[^,]+|,(?=(?:[^"]*"[^"]*")*[^"]*$)', metadata_str)

        for line in lines:
            line = line.strip()
            if not line or line == ",":
                continue

            # Check if this line contains a key-value pair
            key_value_match = re.match(r"(\w+)\s*:\s*(.+)", line)

            if key_value_match:
                # If we have a previous key, save it
                if current_key:
                    value = " ".join(current_value).strip()
                    metadata[current_key] = self._convert_value(value)

                # Start new key-value pair
                current_key = key_value_match.group(1).strip()
                current_value = [key_value_match.group(2).strip()]
            else:
                # Continue previous value
                current_value.append(line)

        # Save the last key-value pair
        if current_key:
            value = " ".join(current_value).strip()
            metadata[current_key] = self._convert_value(value)

        return metadata, clean_desc

    def _convert_value(self, value: str) -> Any:
        """Convert string values to appropriate Python types"""
        # Remove quotes from quoted strings
        if value.startswith('"') and value.endswith('"'):
            return value[1:-1]

        # Handle boolean values
        if value.lower() == "true":
            return True
        if value.lower() == "false":
            return False

        # Handle numeric values
        try:
            if value.isdigit():
                return int(value)
            if value.replace(".", "").isdigit():
                return float(value)
        except ValueError:
            pass

        return value

    def _merge_metadata(
        self, existing: Dict[str, Any], new: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge new metadata with existing metadata, updating values"""
        merged = existing.copy()
        merged["metadata"].update(new["metadata"])
        if new["description"]:
            merged["description"] = new["description"]
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

            # If field already exists, merge the metadata
            if field_name in self.processor.field_metadata[parent_type]:
                self.processor.field_metadata[parent_type][field_name] = (
                    self.processor._merge_metadata(
                        self.processor.field_metadata[parent_type][field_name],
                        new_field_data,
                    )
                )
            else:
                self.processor.field_metadata[parent_type][field_name] = new_field_data
