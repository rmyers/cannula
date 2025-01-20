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
from cannula.errors import SchemaValidationError
from cannula.format import format_code
from cannula.types import Field


class SQLAlchemyGenerator(CodeGenerator):
    """Generates SQLAlchemy models from GraphQL schema."""

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

    def create_field_definition(
        self, field: Field, type_info: ObjectType
    ) -> ast.AnnAssign:
        """Create field definition AST node based on field type and metadata."""

        func_name = "mapped_column"
        args, keywords = self.create_column_args(
            field.name, field.field_type.required, field.metadata
        )
        # Create the Mapped[Type] annotation
        mapped_type = ast_for_subscript(ast_for_name("Mapped"), field.field_type.type)

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
            type_params=[],  # type: ignore
        )

    def validate_relationships(self) -> None:
        """Validate that relationships reference valid database tables and have proper foreign keys."""
        db_tables = [t.db_table for t in self.get_db_types()]

        for type_info in self.analyzer.object_types:
            if "db_table" not in type_info.metadata:
                continue

            for field in type_info.fields:
                if fk := field.metadata.get("foreign_key"):
                    _table, _column = fk.split(".")
                    # Ensure the related type is also a database table
                    print(db_tables, _table)
                    if _table not in db_tables:
                        raise SchemaValidationError(
                            f"{field} references foreign_key '{fk}' "
                            "which is not marked as a database table"
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
                type_params=[],  # type: ignore
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
