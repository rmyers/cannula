from typing import Any, Dict, List
import ast

from cannula.utils import (
    PASS,
    ast_for_annotation_assignment,
    ast_for_assign,
    ast_for_docstring,
    ast_for_keyword,
    ast_for_name,
    ast_for_subscript,
)
from cannula.codegen.schema_analyzer import ObjectType, CodeGenerator
from cannula.format import format_code
from cannula.types import Field


class SchemaValidationError(Exception):
    """Raised when the GraphQL schema metadata is invalid for SQLAlchemy model generation."""

    pass


class SQLAlchemyGenerator(CodeGenerator):
    """Generates SQLAlchemy models from GraphQL schema."""

    def validate_relationship_metadata(
        self, field: Field, type_info: ObjectType
    ) -> None:
        """Validate basic structure of relationship metadata."""
        if not field.metadata.get("relation"):
            return

        relation_metadata = field.metadata["relation"]
        if not isinstance(relation_metadata, dict):
            raise SchemaValidationError(
                f"Relation metadata for {type_info.name}.{field.name} must be a dictionary"
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

    def get_primary_key_fields(self, type_info: ObjectType) -> List[str]:
        """Get list of field names that are marked as primary keys."""
        primary_keys = []
        for field in type_info.fields:
            if field.metadata.get("primary_key"):
                primary_keys.append(field.name)
        return primary_keys

    def create_column_args(
        self, field_name: str, is_required: bool, metadata: Dict[str, Any]
    ) -> tuple[list[ast.expr], list[ast.keyword]]:
        """Create SQLAlchemy Column arguments for a regular column."""
        args: list[ast.expr] = []
        keywords: list[ast.keyword] = []

        # Validate metadata against schema
        self.validate_field_metadata(field_name, is_required, metadata)

        # Handle primary key
        is_primary_key = metadata.get("primary_key", False)
        if is_primary_key:
            keywords.append(ast_for_keyword("primary_key", True))

        # Handle foreign key
        if foreign_key := metadata.get("foreign_key"):
            keywords.append(
                # This does not use a constant so we cannot use ast_for_keyword
                ast.keyword(
                    arg="foreign_key",
                    value=ast.Call(
                        func=ast_for_name("ForeignKey"),
                        args=[ast.Constant(value=foreign_key)],
                        keywords=[],
                    ),
                )
            )

        # Handle index
        if not is_primary_key and metadata.get("index"):
            keywords.append(ast_for_keyword(arg="index", value=True))

        # Handle unique constraint
        if not is_primary_key and metadata.get("unique"):
            keywords.append(ast_for_keyword(arg="unique", value=True))

        # Handle custom column name
        if db_column := metadata.get("db_column"):
            keywords.append(ast_for_keyword(arg="name", value=db_column))

        # Handle nullable based on GraphQL schema
        if not is_primary_key:
            metadata_nullable = metadata.get("nullable")
            # GraphQL non-null fields are not nullable unless explicitly overridden
            nullable = (
                not is_required if metadata_nullable is None else metadata_nullable
            )
            keywords.append(ast_for_keyword(arg="nullable", value=nullable))

        return args, keywords

    def get_db_type(self, type_name: str) -> str:
        """Get the SQLAlchemy type for a given GraphQL type."""
        return next(
            (
                type_info.db_type
                for type_info in self.analyzer.object_types
                if type_name == type_info.py_type
            ),
            type_name,
        )

    def create_relationship_args(
        self, field: Field, metadata: Dict[str, Any]
    ) -> tuple[list[ast.expr], list[ast.keyword]]:
        """Create SQLAlchemy relationship arguments."""
        args: list[ast.expr] = []
        keywords: list[ast.keyword] = []

        relation_metadata = metadata.get("relation", {})

        # Add the related class name as first argument
        relation_value = self.get_db_type(
            field.field_type.of_type or field.field_type.safe_value
        )
        args.append(ast.Constant(value=relation_value))

        # Add keyword arguments specified in metadata (e.g. back_populates)
        for key, value in relation_metadata.items():
            keywords.append(ast_for_keyword(key, value))

        return args, keywords

    def create_field_definition(
        self, field: Field, type_info: ObjectType
    ) -> ast.AnnAssign:
        """Create field definition AST node based on field type and metadata."""
        # Validate relationship metadata if present
        self.validate_relationship_metadata(field, type_info)

        # Handle relationship fields
        if field.metadata.get("relation"):
            func_name = "relationship"
            args, keywords = self.create_relationship_args(field, field.metadata)
            # Create the Mapped[DBType] annotation
            relation_value = self.get_db_type(
                field.field_type.of_type or field.field_type.safe_value
            )
            mapped_type = ast_for_subscript(ast_for_name("Mapped"), relation_value)
        else:
            func_name = "mapped_column"
            args, keywords = self.create_column_args(
                field.name, field.field_type.required, field.metadata
            )
            # Create the Mapped[Type] annotation
            mapped_type = ast_for_subscript(
                ast_for_name("Mapped"), field.field_type.type
            )

        return ast_for_annotation_assignment(
            target=field.name,
            annotation=mapped_type,
            default=ast.Call(
                func=ast_for_name(func_name),
                args=args,
                keywords=keywords,
            ),
        )

    def create_model_class(self, type_info: ObjectType) -> ast.ClassDef:
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

        body: List[ast.stmt] = []

        # Add docstring if present
        if type_info.description:
            body.append(ast_for_docstring(type_info.description))

        # Add table name
        table_name = type_info.metadata.get("db_table", type_info.name.lower())
        body.append(
            ast_for_assign(
                "__tablename__",
                value=ast.Constant(value=table_name),
            )
        )

        # Add fields
        for field in type_info.fields:
            if field.is_computed:
                continue

            field_def = self.create_field_definition(field, type_info)
            body.append(field_def)

        return ast.ClassDef(
            name=type_info.db_type,
            bases=[ast_for_name("Base")],
            keywords=[],
            body=body,
            decorator_list=[],
            type_params=[],
        )

    def validate_relationships(self) -> None:
        """Validate that relationships reference valid database tables and have proper foreign keys."""
        db_tables = [t.db_type for t in self.get_db_types()]

        for type_info in self.analyzer.object_types:
            if "db_table" not in type_info.metadata:
                continue

            for field in type_info.fields:
                if not field.metadata.get("relation"):
                    continue

                # Get the related type (handle both direct and sequence relationships)
                related_type = self.get_db_type(
                    field.field_type.of_type or field.field_type.safe_value
                )
                schema_type = field.field_type.of_type or field.field_type.safe_value

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
                        schema_type
                    )

                    if not referenced_type:
                        raise SchemaValidationError(
                            f"Relationship {type_info.name}.{field.name} references non-existent type {schema_type}"
                        )

                    # Find field by name in referenced type
                    referenced_fields = {f.name: f for f in referenced_type.fields}
                    if referenced_field not in referenced_fields:
                        raise SchemaValidationError(
                            f"Relationship {type_info.name}.{field.name} references non-existent field "
                            f"{referenced_field} in type {schema_type}"
                        )

                # For many-to-one or one-to-one relationships, ensure there's a foreign key
                if not field.field_type.is_list:
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
        db_tables = self.get_db_types()
        if not db_tables:
            return ""

        # Create base class definition
        body: list[ast.stmt] = [
            ast.ClassDef(
                name="Base",
                bases=[ast_for_name("DeclarativeBase")],
                keywords=[],
                body=[PASS],
                decorator_list=[],
                type_params=[],
            )
        ]

        # Generate model classes for each type
        for type_info in self.analyzer.object_types:
            if "db_table" not in type_info.metadata:
                continue

            model_class = self.create_model_class(type_info)
            body.append(model_class)

        # Validate all relationships
        self.validate_relationships()

        # Create and format the complete module
        module = self.create_module(body)
        return format_code(module)
