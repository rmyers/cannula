from typing import Any, Dict, List, Optional, Set, Union
import ast

from graphql import GraphQLObjectType, DocumentNode
from cannula.scalars import ScalarInterface
from cannula.codegen.base import (
    PASS,
    #  ast_for_annotation_assignment,
    ast_for_assign,
    ast_for_constant,
    ast_for_docstring,
    ast_for_keyword,
    ast_for_name,
    # ast_for_subscript,
)
from cannula.codegen.schema_analyzer import SchemaAnalyzer, TypeInfo, CodeGenerator
from cannula.schema import build_and_extend_schema
from cannula.format import format_code
from cannula.codegen.generate_types import _IMPORTS
from cannula.types import Field, FieldType


class SchemaValidationError(Exception):
    """Raised when the GraphQL schema metadata is invalid for SQLAlchemy model generation."""

    pass


class SQLAlchemyGenerator(CodeGenerator):
    """Generates SQLAlchemy models from GraphQL schema."""

    def is_sequence_type(self, field_type: FieldType) -> bool:
        """Check if a field type is a sequence (list) type."""
        return field_type.value is not None and field_type.value.startswith("Sequence[")

    def get_sequence_type(self, field_type: FieldType) -> Optional[str]:
        """Extract the inner type from a sequence type."""
        if not self.is_sequence_type(field_type):
            return None
        # Extract type from Sequence[Type]
        inner_type = field_type.safe_value[9:-1]  # Remove 'Sequence[' and ']'
        return inner_type

    def validate_relationship_metadata(
        self, field: Field, type_info: TypeInfo[GraphQLObjectType]
    ) -> None:
        """Validate basic structure of relationship metadata."""
        if not field.metadata.get("relation"):
            return

        relation_metadata = field.metadata["relation"]
        if not isinstance(relation_metadata, dict):
            raise SchemaValidationError(
                f"Relation metadata for {type_info.name}.{field.name} must be a dictionary"
            )

        # Validate optional cascade value if present
        if "cascade" in relation_metadata:
            cascade = relation_metadata["cascade"]
            if not isinstance(cascade, str):
                raise SchemaValidationError(
                    f"Cascade option in relationship {type_info.name}.{field.name} must be a string"
                )

    def validate_field_metadata(
        self, field_name: str, is_required: bool, metadata: Dict[str, Any]
    ) -> None:
        """Validate that field metadata doesn't conflict with GraphQL schema definitions."""
        metadata_nullable = metadata.get("nullable")

        if is_required and metadata_nullable is True:
            raise SchemaValidationError(
                f"Field '{field_name}' is marked as non-null in GraphQL schema, "
                "but metadata specifies nullable=true. Remove the nullable metadata "
                "or update the GraphQL schema."
            )

    def get_primary_key_fields(
        self, type_info: TypeInfo[GraphQLObjectType]
    ) -> List[str]:
        """Get list of field names that are marked as primary keys."""
        primary_keys = []
        for field in type_info.fields:
            if field.metadata.get("primary_key"):
                primary_keys.append(field.name)
        return primary_keys

    def create_column_args(
        self, field_name: str, is_required: bool, metadata: Dict[str, Any]
    ) -> tuple[list[ast.expr], list[ast.keyword]]:
        """Create SQLAlchemy Column arguments based on field metadata."""
        args: list[ast.expr] = []
        keywords: list[ast.keyword] = []

        # Validate metadata against schema
        self.validate_field_metadata(field_name, is_required, metadata)

        # Handle foreign key
        if foreign_key := metadata.get("foreign_key"):
            on_delete = metadata.get("ondelete")
            on_update = metadata.get("onupdate")
            keywords.append(
                ast.keyword(
                    arg="foreign_key",
                    value=ast.Call(
                        func=ast.Name(id="ForeignKey", ctx=ast.Load()),
                        args=[ast.Constant(value=foreign_key)],
                        keywords=[
                            ast_for_keyword("ondelete", on_delete),
                            ast_for_keyword("onupdate", on_update),
                        ],
                    ),
                )
            )

        # Handle primary key
        is_primary_key = metadata.get("primary_key", False)
        if is_primary_key:
            keywords.append(ast_for_keyword("primary_key", True))

        # Handle index
        if not is_primary_key and metadata.get("index"):
            keywords.append(ast_for_keyword("index", True))

        # Handle unique constraint
        if not is_primary_key and metadata.get("unique"):
            keywords.append(ast_for_keyword("unique", True))

        # Handle custom column name
        if db_column := metadata.get("db_column"):
            keywords.append(ast_for_keyword("name", db_column))

        # Handle nullable based on GraphQL schema
        if not is_primary_key:
            metadata_nullable = metadata.get("nullable")
            # GraphQL non-null fields are not nullable unless explicitly overridden
            nullable = (
                not is_required if metadata_nullable is None else metadata_nullable
            )
            keywords.append(ast_for_keyword("nullable", nullable))

        return args, keywords

    def create_relationship_args(
        self, field: Field, metadata: Dict[str, Any]
    ) -> tuple[list[ast.expr], list[ast.keyword]]:
        """Create SQLAlchemy relationship arguments."""
        args: list[ast.expr] = []
        keywords: list[ast.keyword] = []

        relation_metadata = metadata.get("relation", {})

        # Add the related class name as first argument
        related_type = (
            self.get_sequence_type(field.field_type) or field.field_type.value
        )
        if related_type:
            args.append(ast.Constant(value=related_type))

        # Add back_populates
        if back_populates := relation_metadata.get("back_populates"):
            keywords.append(
                ast.keyword(
                    arg="back_populates", value=ast.Constant(value=back_populates)
                )
            )

        # Add cascade if specified
        if cascade := relation_metadata.get("cascade"):
            keywords.append(
                ast.keyword(arg="cascade", value=ast.Constant(value=cascade))
            )

        return args, keywords

    def create_field_definition(
        self, field: Field, type_info: TypeInfo[GraphQLObjectType]
    ) -> ast.AnnAssign:
        """Create field definition AST node based on field type and metadata."""
        # Validate relationship metadata if present
        self.validate_relationship_metadata(field, type_info)

        # Handle relationship fields
        if field.metadata.get("relation"):
            args, keywords = self.create_relationship_args(field, field.metadata)
            func_name = "relationship"
        else:
            args, keywords = self.create_column_args(
                field.name, field.field_type.required, field.metadata
            )
            func_name = "mapped_column"

        # Create the Mapped[Type] annotation
        mapped_type = ast.Subscript(
            value=ast.Name(id="Mapped", ctx=ast.Load()),
            slice=ast.Name(id=field.field_type.type, ctx=ast.Load()),
            ctx=ast.Load(),
        )

        return ast.AnnAssign(
            target=ast.Name(id=field.name, ctx=ast.Store()),
            annotation=mapped_type,
            value=ast.Call(
                func=ast.Name(id=func_name, ctx=ast.Load()),
                args=args,
                keywords=keywords,
            ),
            simple=1,
        )

    def create_model_class(
        self, type_info: TypeInfo[GraphQLObjectType]
    ) -> ast.ClassDef:
        """Create an AST ClassDef node for a SQLAlchemy model."""
        # Check for multiple primary keys
        primary_keys = self.get_primary_key_fields(type_info)

        if len(primary_keys) > 1 and not type_info.metadata.get(
            "composite_primary_key"
        ):
            error_msg = (
                f"Multiple primary keys found in type '{type_info.name}': {', '.join(primary_keys)}. "
                "To create a composite primary key, add 'composite_primary_key: true' to the type's metadata."
            )
            raise SchemaValidationError(error_msg)

        db_model_name = type_info.type_def.extensions.get(
            "db_type", f"DB{type_info.name}"
        )

        body: List[ast.stmt] = []

        # Add docstring if present
        if type_info.description:
            body.append(ast_for_docstring(type_info.description))

        # Add table name
        table_name = type_info.metadata.get("db_table", type_info.name.lower())
        body.append(ast_for_assign("__tablename__", ast_for_constant(table_name)))

        # Add columns
        for field in type_info.fields:
            # Skip computed fields as they are not stored in the database
            if field.is_computed:
                continue

            field_def = self.create_field_definition(field, type_info)
            body.append(field_def)

        return ast.ClassDef(
            name=db_model_name,
            bases=[ast_for_name("Base")],
            keywords=[],
            body=body,
            decorator_list=[],
        )

    def get_db_table_types(self) -> Set[str]:
        """Get all types that have db_table metadata."""
        return {
            type_info.name
            for type_info in self.analyzer.object_types
            if "db_table" in type_info.metadata
        }

    def validate_relationships(self) -> None:
        """Validate that relationships reference valid database tables and have proper foreign keys."""
        db_tables = self.get_db_table_types()

        for type_info in self.analyzer.object_types:
            if "db_table" not in type_info.metadata:
                continue

            for field in type_info.fields:
                if not field.metadata.get("relation"):
                    continue

                # Get the related type (handle both direct and sequence relationships)
                related_type = (
                    self.get_sequence_type(field.field_type) or field.field_type.value
                )

                # Ensure the related type is also a database table
                if related_type not in db_tables:
                    raise SchemaValidationError(
                        f"Relationship {type_info.name}.{field.name} references type {related_type} "
                        "which is not marked as a database table"
                    )

                relation_metadata = field.metadata.get("relation", {})
                if "back_populates" in relation_metadata:
                    # If back_populates is specified, ensure the referenced model exists
                    referenced_field = relation_metadata["back_populates"]
                    referenced_type = self.analyzer.object_types_by_name.get(
                        related_type
                    )

                    if not referenced_type:
                        raise SchemaValidationError(
                            f"Relationship {type_info.name}.{field.name} references non-existent type {related_type}"
                        )

                    # Find field by name in referenced type
                    referenced_fields = {f.name: f for f in referenced_type.fields}
                    if referenced_field not in referenced_fields:
                        raise SchemaValidationError(
                            f"Relationship {type_info.name}.{field.name} references non-existent field "
                            f"{referenced_field} in type {related_type}"
                        )

                # For many-to-one or one-to-one relationships, ensure there's a foreign key
                if not self.is_sequence_type(field.field_type):
                    fk_field = next(
                        (f for f in type_info.fields if f.metadata.get("foreign_key")),
                        None,
                    )
                    if not fk_field:
                        raise SchemaValidationError(
                            f"Relationship {type_info.name}.{field.name} to {related_type} "
                            "requires a foreign key field"
                        )

    def generate(self) -> str:
        """Generate SQLAlchemy models from the schema."""
        # Create base class definition
        body: list[ast.stmt] = [
            ast.ClassDef(
                name="Base",
                bases=[ast_for_name("DeclarativeBase")],
                keywords=[],
                body=[PASS],
                decorator_list=[],
            )
        ]

        # Generate model classes for each type
        for type_info in self.analyzer.object_types:
            if "db_table" not in type_info.metadata:
                continue

            model_class = self.create_model_class(type_info)
            body.append(model_class)

        print(self.relationships)
        # Validate all relationships
        self.validate_relationships()

        # Create and format the complete module
        module = self.create_module(body)
        return format_code(module)


def render_sql_models(
    type_defs: List[Union[str, DocumentNode]],
    scalars: List[ScalarInterface] = [],
) -> str:
    """Generate SQLAlchemy models from GraphQL schema"""
    schema = build_and_extend_schema(type_defs, scalars, {"imports": _IMPORTS})
    analyzer = SchemaAnalyzer(schema)
    generator = SQLAlchemyGenerator(analyzer)
    return generator.generate()
