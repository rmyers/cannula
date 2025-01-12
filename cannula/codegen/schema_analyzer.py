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
    Generic,
    List,
    Optional,
    Protocol,
    TypeVar,
    cast,
)

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
from cannula.types import Field, InputType, InterfaceType, UnionType
from cannula.utils import ast_for_import_from

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
        return self.type_metadata.get(type_name, {})

    def get_field_metadata(self, type_name: str, field_name: str) -> Dict[str, Any]:
        """Get metadata for a specific field"""
        return self.field_metadata.get(type_name, {}).get(str(field_name), {})


@dataclass
class TypeInfo(Generic[T]):
    """Container for type information and metadata"""

    type_def: T
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
        """Pluralized name used for the attribute on the context object.

        Follows English pluralization rules.
        """
        _attr = self.name.lower()

        # Special cases and irregular plurals could be added here
        irregular_plurals = {
            "person": "people",
            "child": "children",
            "goose": "geese",
            "mouse": "mice",
            "criterion": "criteria",
        }
        if _attr in irregular_plurals:
            return irregular_plurals[_attr]

        # Words ending in -is change to -es
        if _attr.endswith("is"):
            return f"{_attr[:-2]}es"

        # Words ending in -us change to -i
        if _attr.endswith("us"):
            return f"{_attr[:-2]}i"

        # Words ending in -on change to -a
        if _attr.endswith("on"):
            return f"{_attr[:-2]}a"

        # Words ending in sibilant sounds (s, sh, ch, x) add -es
        if _attr.endswith(("s", "sh", "ch", "x", "zz")):
            return f"{_attr}es"

        # Words ending in -z double the z and add -es
        if _attr.endswith("z"):
            return f"{_attr}zes"

        # Words ending in consonant + y change y to ies
        if _attr.endswith("y") and len(_attr) > 1 and _attr[-2] not in "aeiou":
            return f"{_attr[:-1]}ies"

        # Words ending in -f or -fe change to -ves
        if _attr.endswith("fe"):
            return f"{_attr[:-2]}ves"
        if _attr.endswith("f"):
            return f"{_attr[:-1]}ves"

        # Words ending in -o: some add -es, most just add -s
        o_es_endings = {
            "hero",
            "potato",
            "tomato",
            "echo",
            "veto",
            "volcano",
            "tornado",
        }
        if _attr in o_es_endings:
            return f"{_attr}es"

        # Default case: just add s
        return f"{_attr}s"


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
        self.interface_types: List[InterfaceType] = []
        self.input_types: List[InputType] = []
        self.union_types: List[UnionType] = []
        self.operation_types: List[TypeInfo[GraphQLObjectType]] = []
        self.operation_fields: List[Field] = []
        # Add helper to access object types by name
        self.object_types_by_name: Dict[str, TypeInfo[GraphQLObjectType]] = {}

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
        fields = [
            self.get_field(
                field_name=field_name,
                field_def=field_def,
                parent=node.name,
            )
            for field_name, field_def in node.fields.items()
        ]
        return InterfaceType(
            node=node,
            name=node.name,
            py_type=node.name,
            fields=fields,
            metadata=metadata,
            description=metadata.get("description"),
        )

    def parse_input(self, node: GraphQLInputObjectType) -> InputType:
        """Parse a GraphQL Input type into InputType object."""
        metadata = self.extensions.get_type_metadata(node.name)
        fields = [
            self.get_field(
                field_name=field_name,
                field_def=field_def,
                parent=node.name,
            )
            for field_name, field_def in node.fields.items()
        ]
        return InputType(
            node=node,
            name=node.name,
            py_type=node.name,
            fields=fields,
            metadata=metadata,
            description=metadata.get("description"),
        )

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


class CodeGenerator(ABC):
    """Base class for code generators with common functionality."""

    def __init__(self, analyzer: SchemaAnalyzer):
        self.analyzer = analyzer
        self.schema = analyzer.schema
        self.imports = analyzer.extensions.imports

    def get_db_types(self) -> List[TypeInfo[GraphQLObjectType]]:
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
