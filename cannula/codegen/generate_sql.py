from typing import Any, Dict, List, Union
import ast

from graphql import GraphQLObjectType, DocumentNode
from cannula.scalars import ScalarInterface
from cannula.codegen.base import ast_for_docstring
from cannula.codegen.schema_analyzer import SchemaAnalyzer, TypeInfo, CodeGenerator
from cannula.schema import build_and_extend_schema
from cannula.format import format_code
from cannula.codegen.generate_types import _IMPORTS


class SchemaValidationError(Exception):
    """Raised when the GraphQL schema metadata is invalid for SQLAlchemy model generation."""

    pass


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

        # Handle primary key
        is_primary_key = metadata.get("primary_key", False)
        if is_primary_key:
            keywords.append(
                ast.keyword(arg="primary_key", value=ast.Constant(value=True))
            )

        # Handle index
        if not is_primary_key and metadata.get("index"):
            keywords.append(ast.keyword(arg="index", value=ast.Constant(value=True)))

        # Handle unique constraint
        if not is_primary_key and metadata.get("unique"):
            keywords.append(ast.keyword(arg="unique", value=ast.Constant(value=True)))

        # Handle custom column name
        if db_column := metadata.get("db_column"):
            keywords.append(
                ast.keyword(arg="name", value=ast.Constant(value=db_column))
            )

        # Handle nullable based on GraphQL schema
        if not is_primary_key:
            metadata_nullable = metadata.get("nullable")
            # GraphQL non-null fields are not nullable unless explicitly overridden
            nullable = (
                not is_required if metadata_nullable is None else metadata_nullable
            )
            keywords.append(
                ast.keyword(arg="nullable", value=ast.Constant(value=nullable))
            )

        return args, keywords

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

        body: List[ast.stmt] = []

        # Add docstring if present
        if type_info.description:
            body.append(ast_for_docstring(type_info.description))

        # Add table name
        table_name = type_info.metadata.get("db_table", type_info.name.lower())
        body.append(
            ast.Assign(
                targets=[ast.Name(id="__tablename__", ctx=ast.Store())],
                value=ast.Constant(value=table_name),
            )
        )

        # Add columns
        for field in type_info.fields:
            args, keywords = self.create_column_args(
                field.name, field.field_type.required, field.metadata
            )

            # Create the Mapped[Type] annotation
            mapped_type = ast.Subscript(
                value=ast.Name(id="Mapped", ctx=ast.Load()),
                slice=ast.Name(id=field.type, ctx=ast.Load()),
                ctx=ast.Load(),
            )

            column_def = ast.AnnAssign(
                target=ast.Name(id=field.name, ctx=ast.Store()),
                annotation=mapped_type,
                value=ast.Call(
                    func=ast.Name(id="mapped_column", ctx=ast.Load()),
                    args=args,
                    keywords=keywords,
                ),
                simple=1,
            )
            body.append(column_def)

        return ast.ClassDef(
            name=type_info.name,
            bases=[ast.Name(id="Base", ctx=ast.Load())],
            keywords=[],
            body=body,
            decorator_list=[],
        )

    def generate(self) -> str:
        """Generate SQLAlchemy models from the schema."""
        # Create base class definition
        body: list[ast.stmt] = [
            ast.ClassDef(
                name="Base",
                bases=[ast.Name(id="DeclarativeBase", ctx=ast.Load())],
                keywords=[],
                body=[ast.Pass()],
                decorator_list=[],
            )
        ]

        # Generate model classes for each type
        for type_info in self.analyzer.object_types:
            if "db_table" not in type_info.metadata:
                continue
            model_class = self.create_model_class(type_info)
            body.append(model_class)

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
