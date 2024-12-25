"""
Proposed refactor of the schema parsing and code generation system.
Key changes:
1. Eliminate redundant dataclasses by using GraphQL types directly
2. Better separation of concerns between parsing and code generation
3. Unified metadata handling
4. Type-safe schema extensions
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, Generic, List, Optional, Protocol, TypeVar, cast

from graphql import (
    GraphQLField,
    GraphQLSchema,
    GraphQLNamedType,
    GraphQLObjectType,
    GraphQLInterfaceType,
    GraphQLInputObjectType,
    GraphQLUnionType,
    is_input_object_type,
    is_interface_type,
    is_object_type,
    is_union_type,
)

from cannula.codegen.parse_args import parse_field_arguments
from cannula.codegen.parse_type import parse_graphql_type
from cannula.types import Field, UnionType

LOG = logging.getLogger(__name__)

# Type Definitions
T = TypeVar("T", bound=GraphQLNamedType)


class MetadataProvider(Protocol):
    """Protocol for accessing type and field metadata"""

    @property
    def type_metadata(self) -> Dict[str, Dict[str, Any]]: ...

    @property
    def field_metadata(self) -> Dict[str, Dict[str, Dict[str, Any]]]: ...


class SchemaExtension:
    """Container for schema-wide extensions and metadata"""

    def __init__(self, schema: GraphQLSchema) -> None:
        self.schema = schema
        self._type_metadata = schema.extensions.get("type_metadata", {})
        self._field_metadata = schema.extensions.get("field_metadata", {})
        self._imports = schema.extensions.get("imports", {})

    @property
    def type_metadata(self) -> Dict[str, Dict[str, Any]]:
        return self._type_metadata

    @property
    def field_metadata(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        return self._field_metadata

    @property
    def imports(self) -> Dict[str, set[str]]:
        return self._imports

    def get_type_metadata(self, type_name: str) -> Dict[str, Any]:
        """Get metadata for a specific type"""
        return self._type_metadata.get(type_name, {})

    def get_field_metadata(self, type_name: str, field_name: str) -> Dict[str, Any]:
        """Get metadata for a specific field"""
        return self._field_metadata.get(type_name, {}).get(str(field_name), {})


@dataclass
class TypeInfo(Generic[T]):
    """Container for type information and metadata"""

    type_def: T
    name: str
    py_type: str
    metadata: Dict[str, Any]
    fields: List[Field]
    description: Optional[str] = None


class SchemaAnalyzer:
    """
    Analyzes a GraphQL schema and provides high-level access to type information
    with associated metadata.
    """

    def __init__(self, schema: GraphQLSchema) -> None:
        self.schema = schema
        self.extensions = SchemaExtension(schema)
        self._analyze()

    def _analyze(self) -> None:
        """Analyze schema and categorize types"""
        self.object_types: List[TypeInfo[GraphQLObjectType]] = []
        self.interface_types: List[TypeInfo[GraphQLInterfaceType]] = []
        self.input_types: List[TypeInfo[GraphQLInputObjectType]] = []
        self.union_types: List[UnionType] = []
        self.operation_types: List[TypeInfo[GraphQLObjectType]] = []
        self.operation_fields: List[Field] = []

        for name, type_def in self.schema.type_map.items():
            is_operation = name in ("Query", "Mutation", "Subscription")
            is_private = name.startswith("__")

            if is_private:
                continue
            elif is_operation:
                type_def = cast(GraphQLObjectType, type_def)
                type_info = self.get_type_info(type_def)
                self.operation_types.append(type_info)
                self.operation_fields.extend(type_info.fields)
            elif is_object_type(type_def):
                type_def = cast(GraphQLObjectType, type_def)
                self.object_types.append(self.get_type_info(type_def))
            elif is_interface_type(type_def):
                type_def = cast(GraphQLInterfaceType, type_def)
                self.interface_types.append(self.get_type_info(type_def))
            elif is_input_object_type(type_def):
                type_def = cast(GraphQLInputObjectType, type_def)
                self.input_types.append(self.get_type_info(type_def))
            elif is_union_type(type_def):
                type_def = cast(GraphQLUnionType, type_def)
                self.union_types.append(self.parse_union(type_def))

        # Sort types and fields
        self.input_types.sort(key=lambda o: o.name)
        self.interface_types.sort(key=lambda o: o.name)
        self.object_types.sort(key=lambda o: o.name)
        self.operation_fields.sort(key=lambda o: o.name)
        self.operation_types.sort(key=lambda o: o.name)
        self.union_types.sort(key=lambda o: o.name)

    def parse_union(self, node: GraphQLUnionType) -> UnionType:
        """Parse a GraphQL Union type into a UnionType object"""
        metadata = self.extensions.get_type_metadata(node.name)
        types = [parse_graphql_type(t, self.schema.type_map) for t in node.types]

        return UnionType(
            name=node.name,
            py_type=metadata.get("py_type", node.name),
            description=metadata.get("description"),
            types=types,
        )

    def get_field(self, field_name: str, field_def: GraphQLField, parent: str) -> Field:
        field_type = parse_graphql_type(field_def.type, self.schema.type_map)
        metadata = self.extensions.get_field_metadata(parent, field_name)
        directives = metadata.get("directives", [])
        args = parse_field_arguments(field_def, self.schema.type_map)
        return Field.from_field(
            name=field_name,
            field=field_def,
            metadata=metadata,
            parent=parent,
            field_type=field_type,
            args=args,
            directives=directives,
        )

    def get_type_info(self, gql_type: T) -> TypeInfo[T]:
        """Get type information for a specific type"""
        metadata = self.extensions.get_type_metadata(gql_type.name)
        _fields = getattr(gql_type, "fields", {})
        fields = [
            self.get_field(
                field_name=field_name,
                field_def=field_def,
                parent=gql_type.name,
            )
            for field_name, field_def in _fields.items()
        ]

        return TypeInfo(
            type_def=gql_type,
            name=gql_type.name,
            py_type=gql_type.extensions.get("py_type", gql_type.name),
            description=metadata.get("description"),
            metadata=metadata.get("metadata", {}),
            fields=fields,
        )


class CodeGenerator:
    """Base class for code generators"""

    def __init__(self, analyzer: SchemaAnalyzer) -> None:
        self.analyzer = analyzer

    def generate(self) -> str:
        """Generate code from the analyzed schema"""
        raise NotImplementedError
