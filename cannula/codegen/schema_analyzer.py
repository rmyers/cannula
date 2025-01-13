"""
Proposed refactor of the schema parsing and code generation system.
Key changes:
1. Eliminate redundant dataclasses by using GraphQL types directly
2. Better separation of concerns between parsing and code generation
3. Unified metadata handling
4. Type-safe schema extensions
"""

import ast
import collections
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import (
    Any,
    DefaultDict,
    Dict,
    List,
    Optional,
    cast,
)

from graphql import (
    GraphQLField,
    GraphQLSchema,
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
from cannula.types import Field, InputType, InterfaceType, UnionType
from cannula.utils import ast_for_import_from, pluralize

LOG = logging.getLogger(__name__)


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
        return self.type_metadata.get(type_name, {})

    def get_field_metadata(self, type_name: str, field_name: str) -> Dict[str, Any]:
        """Get metadata for a specific field"""
        return self.field_metadata.get(type_name, {}).get(str(field_name), {})


@dataclass
class TypeInfo:
    """Container for type information and metadata"""

    type_def: GraphQLObjectType
    name: str
    py_type: str
    metadata: Dict[str, Any]
    fields: List[Field]
    description: Optional[str] = None

    @property
    def is_db_type(self) -> bool:
        return bool(self.metadata.get("db_table", False))

    @property
    def db_type(self) -> str:
        return self.type_def.extensions.get("db_type", f"DB{self.name}")

    @property
    def context_attr(self) -> str:
        """Pluralized name used for the attribute on the context object."""
        return pluralize(self.name)


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
        self.object_types: List[TypeInfo] = []
        self.interface_types: List[InterfaceType] = []
        self.input_types: List[InputType] = []
        self.union_types: List[UnionType] = []
        self.operation_types: List[TypeInfo] = []
        self.operation_fields: List[Field] = []
        # Add helper to access object types by name
        self.object_types_by_name: Dict[str, TypeInfo] = {}

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
                self.interface_types.append(self.parse_interface(type_def))
            elif is_input_object_type(type_def):
                type_def = cast(GraphQLInputObjectType, type_def)
                self.input_types.append(self.parse_input(type_def))
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
        self.object_types_by_name = {t.py_type: t for t in self.object_types}
        self.forward_references = self.get_forward_references()

    def parse_union(self, node: GraphQLUnionType) -> UnionType:
        """Parse a GraphQL Union type into a UnionType object"""
        metadata = self.extensions.get_type_metadata(node.name)
        types = [parse_graphql_type(t) for t in node.types]

        return UnionType(
            name=node.name,
            py_type=metadata.get("py_type", node.name),
            description=metadata.get("description"),
            types=types,
        )

    def parse_interface(self, node: GraphQLInterfaceType) -> InterfaceType:
        """Parse a GraphQL Interface type into InterfaceType object."""
        metadata = self.extensions.get_type_metadata(node.name)
        return InterfaceType(
            node=node,
            name=node.name,
            py_type=node.name,
            fields=self.get_fields(node),
            metadata=metadata,
            description=metadata.get("description"),
        )

    def parse_input(self, node: GraphQLInputObjectType) -> InputType:
        """Parse a GraphQL Input type into InputType object."""
        metadata = self.extensions.get_type_metadata(node.name)
        return InputType(
            node=node,
            name=node.name,
            py_type=node.name,
            fields=self.get_fields(node),
            metadata=metadata,
            description=metadata.get("description"),
        )

    def get_fields(
        self, node: GraphQLObjectType | GraphQLInputObjectType | GraphQLInterfaceType
    ) -> list[Field]:
        return [
            self.get_field(
                field_name=field_name,
                field_def=field_def,
                parent=node.name,
            )
            for field_name, field_def in node.fields.items()
        ]

    def get_field(self, field_name: str, field_def: GraphQLField, parent: str) -> Field:
        field_type = parse_graphql_type(field_def.type)
        metadata = self.extensions.get_field_metadata(parent, field_name)
        directives = metadata.get("directives", [])
        args = parse_field_arguments(field_def)
        return Field.from_field(
            name=field_name,
            field=field_def,
            metadata=metadata,
            parent=parent,
            field_type=field_type,
            args=args,
            directives=directives,
        )

    def get_forward_references(self) -> DefaultDict[str, list[Field]]:
        # First parse the db_types and add forward reference to relations
        forward_relations: DefaultDict[str, list[Field]] = collections.defaultdict(list)
        for type_info in self.object_types:
            for field in type_info.fields:
                if field.relation and field.field_type.is_object_type:
                    forward_relations[field.field_type.of_type].append(field)

        return forward_relations

    def get_type_info(self, gql_type: GraphQLObjectType) -> TypeInfo:
        """Get type information for a specific type"""
        metadata = self.extensions.get_type_metadata(gql_type.name)

        return TypeInfo(
            type_def=gql_type,
            name=gql_type.name,
            py_type=gql_type.extensions.get("py_type", gql_type.name),
            description=metadata.get("description"),
            metadata=metadata.get("metadata", {}),
            fields=self.get_fields(gql_type),
        )


class CodeGenerator(ABC):
    """Base class for code generators with common functionality."""

    def __init__(self, analyzer: SchemaAnalyzer):
        self.analyzer = analyzer
        self.schema = analyzer.schema
        self.imports = analyzer.extensions.imports

    def get_db_types(self) -> List[TypeInfo]:
        """Get all types that have db_table metadata"""
        return [
            type_info
            for type_info in self.analyzer.object_types
            if type_info.is_db_type
        ]

    def create_import_statements(self) -> List[ast.ImportFrom]:
        """Create AST nodes for import statements."""
        module_imports = sorted(self.imports.keys())
        return [
            ast_for_import_from(module=mod, names=self.imports[mod])
            for mod in module_imports
            if mod != "builtins"
        ]

    def create_module(self, body: List[ast.stmt]) -> ast.Module:
        """Create an AST module with imports and body."""
        imports = self.create_import_statements()
        module = ast.Module(body=imports + body, type_ignores=[])
        return ast.fix_missing_locations(module)

    @abstractmethod
    def generate(self, *args, **kwargs) -> str:  # pragma: no cover
        """Generate the complete code output."""
        raise NotImplementedError("subclasses must provide a generate function")
