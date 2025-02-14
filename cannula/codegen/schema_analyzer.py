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

from cannula.codegen.parse_args import parse_field_arguments, parse_related_args
from cannula.codegen.parse_type import parse_graphql_type
from cannula.types import (
    Field,
    FieldMetadata,
    FieldType,
    InputType,
    InterfaceType,
    ObjectType,
    SQLMetadata,
    UnionType,
)
from cannula.utils import ast_for_import_from

LOG = logging.getLogger(__name__)


class SchemaExtension:
    """Container for schema-wide extensions and metadata"""

    def __init__(self, schema: GraphQLSchema) -> None:
        self.schema = schema
        self._type_metadata = schema.extensions.get("type_metadata", {})
        self._imports = schema.extensions.get("imports", {})

    @property
    def type_metadata(self) -> Dict[str, Dict[str, Any]]:
        return self._type_metadata

    @property
    def imports(self) -> Dict[str, set[str]]:
        return self._imports

    def get_type_metadata(self, type_name: str) -> Dict[str, Any]:
        """Get metadata for a specific type"""
        return self.type_metadata.get(type_name, {})


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
        self.forward_relations: DefaultDict[str, list[Field]] = collections.defaultdict(
            list
        )
        self.object_types: List[ObjectType] = []
        self.interface_types: List[InterfaceType] = []
        self.input_types: List[InputType] = []
        self.union_types: List[UnionType] = []
        self.operation_types: List[ObjectType] = []
        self.operation_fields: List[Field] = []
        # Add helper to access object types by name
        self.object_types_by_name: Dict[str, ObjectType] = {}

        for name, type_def in self.schema.type_map.items():
            is_private = name.startswith("__")

            if is_private:
                continue
            elif is_object_type(type_def):
                type_def = cast(GraphQLObjectType, type_def)
                object_type = self.parse_object(type_def)
                self.get_forward_references(object_type)
                self.object_types_by_name[name] = object_type
            elif is_interface_type(type_def):
                type_def = cast(GraphQLInterfaceType, type_def)
                self.interface_types.append(self.parse_interface(type_def))
            elif is_input_object_type(type_def):
                type_def = cast(GraphQLInputObjectType, type_def)
                self.input_types.append(self.parse_input(type_def))
            elif is_union_type(type_def):
                type_def = cast(GraphQLUnionType, type_def)
                self.union_types.append(self.parse_union(type_def))

        # Parse relations
        for name, obj in self.object_types_by_name.items():
            obj.related_fields = self.forward_relations.get(name, [])

            if name in ("Query", "Mutation", "Subscription"):
                self.operation_types.append(obj)
                self.operation_fields.extend(obj.fields)
            else:
                self.object_types.append(obj)

        # Sort types and fields
        self.input_types.sort(key=lambda o: o.name)
        self.interface_types.sort(key=lambda o: o.name)
        self.object_types.sort(key=lambda o: o.name)
        self.operation_fields.sort(key=lambda o: o.name)
        self.operation_types.sort(key=lambda o: o.name)
        self.union_types.sort(key=lambda o: o.name)
        self.object_types_by_name = {t.py_type: t for t in self.object_types}

    def parse_union(self, node: GraphQLUnionType) -> UnionType:
        """Parse a GraphQL Union type into a UnionType object"""
        metadata = self.extensions.get_type_metadata(node.name)
        types = [parse_graphql_type(t) for t in node.types]

        return UnionType(
            node=node,
            name=node.name,
            py_type=metadata.get("py_type", node.name),
            types=types,
        )

    def parse_interface(self, node: GraphQLInterfaceType) -> InterfaceType:
        """Parse a GraphQL Interface type into InterfaceType object."""
        metadata = self.extensions.get_type_metadata(node.name)
        return InterfaceType(
            node=node,
            name=node.name,
            py_type=node.name,
            fields=self.get_fields(node, metadata),
            metadata=metadata,
        )

    def parse_input(self, node: GraphQLInputObjectType) -> InputType:
        """Parse a GraphQL Input type into InputType object."""
        metadata = self.extensions.get_type_metadata(node.name)
        return InputType(
            node=node,
            name=node.name,
            py_type=node.name,
            fields=self.get_fields(node, metadata),
            metadata=metadata,
        )

    def parse_object(self, node: GraphQLObjectType) -> ObjectType:
        """Parse a GraphQL Object type into ObjectType object."""
        fk_fields: dict[str, GraphQLField] = {}

        for _field_name, field_def in node.fields.items():
            field_meta = cast(
                FieldMetadata,
                field_def.extensions.get("field_meta", FieldMetadata()),
            )
            if fk := field_meta.foreign_key:
                table_name = fk.split(".")[0]
                fk_fields[table_name] = cast(GraphQLField, field_def)

        return ObjectType(
            type_def=node,
            name=node.name,
            py_type=node.extensions.get("py_type", node.name),
            fields=self.get_fields(node, fk_fields),
        )

    def get_fields(
        self,
        node: GraphQLObjectType | GraphQLInputObjectType | GraphQLInterfaceType,
        fk_fields: Dict[str, GraphQLField],
    ) -> list[Field]:
        return [
            self.get_field(
                field_name=field_name,
                field_def=field_def,
                parent=node,
                fk_fields=fk_fields,
            )
            for field_name, field_def in node.fields.items()
        ]

    def get_fk_field(
        self,
        field_type: FieldType,
        parent: GraphQLObjectType | GraphQLInputObjectType | GraphQLInterfaceType,
        fk_fields: Dict[str, GraphQLField],
    ) -> Field | None:
        if not field_type.is_object_type:
            return None

        related_meta = self.extensions.get_type_metadata(field_type.of_type)
        if sql_meta := related_meta.get("sql_metadata"):
            sql_meta = cast(SQLMetadata, sql_meta)
            if fk_field := fk_fields.get(sql_meta.table_name):
                field_type = parse_graphql_type(fk_field.type)
                assert fk_field.ast_node
                field_name = fk_field.ast_node.name.value
                return Field.from_field(
                    name=field_name,
                    field=fk_field,
                    parent=parent.name,
                    field_type=field_type,
                )

        return None

    def get_field(
        self,
        field_name: str,
        field_def: GraphQLField,
        parent: GraphQLObjectType | GraphQLInputObjectType | GraphQLInterfaceType,
        fk_fields: Dict[str, GraphQLField],
    ) -> Field:
        field_type = parse_graphql_type(field_def.type)
        directives = field_def.extensions.get("directives", [])
        fk_field = self.get_fk_field(
            field_type=field_type,
            parent=parent,
            fk_fields=fk_fields,
        )
        args = parse_field_arguments(field_def)
        field_metadata = field_def.extensions.get("field_meta", FieldMetadata())
        related_args = parse_related_args(field_name, field_metadata, parent)
        return Field.from_field(
            name=field_name,
            field=field_def,
            parent=parent.name,
            field_type=field_type,
            args=args,
            related_args=related_args,
            directives=directives,
            fk_field=fk_field,
        )

    def get_forward_references(self, object_type: ObjectType) -> None:
        for field in object_type.fields:
            if field.field_type.is_object_type:
                self.forward_relations[field.field_type.of_type].append(field)


class CodeGenerator(ABC):
    """Base class for code generators with common functionality."""

    def __init__(self, analyzer: SchemaAnalyzer):
        self.analyzer = analyzer
        self.schema = analyzer.schema
        self.imports = analyzer.extensions.imports

    def get_db_types(self) -> List[ObjectType]:
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
    def generate(self, *args, **kwargs) -> Optional[str]:  # pragma: no cover
        """Generate the complete code output."""
        raise NotImplementedError("subclasses must provide a generate function")
