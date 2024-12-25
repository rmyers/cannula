import ast
from typing import Dict, Any, List
from graphql import (
    GraphQLSchema,
    GraphQLObjectType,
    GraphQLField,
    GraphQLType,
    GraphQLNonNull,
    get_named_type,
)
from cannula.codegen.base import fix_missing_locations


class SchemaValidationError(Exception):
    """Raised when the GraphQL schema metadata is invalid for SQLAlchemy model generation."""

    pass


def is_non_null_type(type_: GraphQLType) -> bool:
    """Check if a GraphQL type is non-null."""
    return isinstance(type_, GraphQLNonNull)


def get_base_type(type_: GraphQLType) -> str:
    """Get the base type name from a GraphQL type, ignoring List and NonNull wrappers."""
    named_type = get_named_type(type_)
    return str(named_type)


def get_sqlalchemy_type(graphql_type: GraphQLType) -> str:
    """Map GraphQL types to SQLAlchemy types with reasonable defaults."""
    base_type = get_base_type(graphql_type)
    type_map = {
        "String": "String",
        "Int": "Integer",
        "Float": "Float",
        "Boolean": "Boolean",
        "ID": "String",
        "DateTime": "DateTime",
    }
    return type_map.get(base_type, "String")  # Default to String if unknown


def validate_field_metadata(
    field_name: str, field: GraphQLField, metadata: Dict[str, Any]
) -> None:
    """Validate that field metadata doesn't conflict with GraphQL schema definitions."""
    is_required = is_non_null_type(field.type)
    metadata_nullable = metadata.get("nullable")

    if is_required and metadata_nullable is True:
        raise SchemaValidationError(
            f"Field '{field_name}' is marked as non-null in GraphQL schema (!), "
            "but metadata specifies nullable=true. Remove the nullable metadata "
            "or update the GraphQL schema."
        )


def get_primary_key_fields(
    fields: Dict[str, GraphQLField], field_metadata: Dict[str, Dict[str, Any]]
) -> List[str]:
    """Get list of field names that are marked as primary keys."""
    primary_keys = []
    for field_name, field_meta in field_metadata.items():
        if field_meta.get("metadata", {}).get("primary_key"):
            primary_keys.append(field_name)
    return primary_keys


def create_column_args(
    field_name: str, field: GraphQLField, field_metadata: Dict[str, Any]
) -> list:
    """Create SQLAlchemy Column arguments based on field metadata."""
    args: List[ast.expr | ast.keyword] = []
    metadata = field_metadata.get("metadata", {})

    # Validate metadata against schema
    validate_field_metadata(field_name, field, metadata)

    # Add SQLAlchemy type
    args.append(ast.Name(id=get_sqlalchemy_type(field.type), ctx=ast.Load()))

    is_primary_key = metadata.get("primary_key", False)

    # Handle primary key
    if is_primary_key:
        args.append(ast.keyword(arg="primary_key", value=ast.Constant(value=True)))

    # Handle index (skip if primary key as it's automatically indexed)
    if not is_primary_key and metadata.get("index"):
        args.append(ast.keyword(arg="index", value=ast.Constant(value=True)))

    # Handle unique constraint (skip if primary key as it's automatically unique)
    if not is_primary_key and metadata.get("unique"):
        args.append(ast.keyword(arg="unique", value=ast.Constant(value=True)))

    # Handle custom column name
    if db_column := metadata.get("db_column"):
        args.append(ast.keyword(arg="name", value=ast.Constant(value=db_column)))

    # Handle nullable based on GraphQL schema
    if not is_primary_key:
        # GraphQL non-null fields are not nullable
        nullable = not is_non_null_type(field.type)
        args.append(ast.keyword(arg="nullable", value=ast.Constant(value=nullable)))

    return args


def create_model_class(
    type_name: str,
    fields: Dict[str, GraphQLField],
    type_metadata: Dict[str, Any],
    field_metadata: Dict[str, Dict[str, Any]],
) -> ast.ClassDef:
    """Create an AST ClassDef node for a SQLAlchemy model."""

    # Check for multiple primary keys
    primary_keys = get_primary_key_fields(fields, field_metadata)
    metadata = type_metadata.get("metadata", {})

    if len(primary_keys) > 1 and not metadata.get("composite_primary_key"):
        error_msg = (
            f"Multiple primary keys found in type '{type_name}': {', '.join(primary_keys)}. "
            "To create a composite primary key, add 'composite_primary_key: true' to the type's metadata."
        )
        raise SchemaValidationError(error_msg)

    # Get table name and description from metadata
    table_name = metadata.get("db_table", type_name.lower())
    description = type_metadata.get("description", "")

    # Build docstring content
    docstring = description + "\n\n" if description else ""

    # Add field descriptions to docstring
    field_docs = []
    for field_name, field_meta in field_metadata.items():
        if field_description := field_meta.get("description"):
            field_docs.append(f"    {field_name}: {field_description}")

    if field_docs:
        docstring += "Args:\n" + "\n".join(field_docs)

    # Create docstring node if we have content
    docstring_expr = (
        ast.Expr(value=ast.Constant(value=docstring.strip())) if docstring else None
    )

    # Create __tablename__ assignment
    tablename_assign = ast.Assign(
        targets=[ast.Name(id="__tablename__", ctx=ast.Store())],
        value=ast.Constant(value=table_name),
    )

    # Create column definitions for each field
    column_defs = []
    for field_name, field in fields.items():
        field_meta = field_metadata.get(field_name, {})
        column_args = create_column_args(field_name, field, field_meta)

        column_def = ast.AnnAssign(
            target=ast.Name(id=field_name, ctx=ast.Store()),
            annotation=ast.Name(id="Mapped", ctx=ast.Load()),
            value=ast.Call(
                func=ast.Name(id="mapped_column", ctx=ast.Load()),
                args=column_args,
                keywords=[],
            ),
            simple=1,
        )
        column_defs.append(column_def)

    # Create the class definition with docstring if present
    body = (
        ([docstring_expr] if docstring_expr else []) + [tablename_assign] + column_defs
    )
    class_def = ast.ClassDef(
        name=type_name,
        bases=[ast.Name(id="Base", ctx=ast.Load())],
        keywords=[],
        body=body,  # type: ignore
        decorator_list=[],
    )

    return class_def


def generate_sqlalchemy_models(schema: GraphQLSchema) -> ast.Module:
    """Generate SQLAlchemy models from a GraphQL schema."""

    # Get extensions from schema
    extensions = getattr(schema, "extensions", {})
    type_metadata = extensions.get("type_metadata", {})
    field_metadata = extensions.get("field_metadata", {})

    # Create import statements
    imports = [
        ast.ImportFrom(
            module="typing", names=[ast.alias(name="Annotated", asname=None)], level=0
        ),
        ast.ImportFrom(
            module="sqlalchemy",
            names=[
                ast.alias(name="Integer", asname=None),
                ast.alias(name="String", asname=None),
                ast.alias(name="Boolean", asname=None),
                ast.alias(name="Float", asname=None),
                ast.alias(name="DateTime", asname=None),
            ],
            level=0,
        ),
        ast.ImportFrom(
            module="sqlalchemy.orm",
            names=[
                ast.alias(name="DeclarativeBase", asname=None),
                ast.alias(name="Mapped", asname=None),
                ast.alias(name="mapped_column", asname=None),
            ],
            level=0,
        ),
    ]

    # Create Base class definition
    base_class = ast.ClassDef(
        name="Base",
        bases=[ast.Name(id="DeclarativeBase", ctx=ast.Load())],
        keywords=[],
        body=[ast.Pass()],
        decorator_list=[],
    )

    # Generate model classes for each type
    model_classes = []
    for type_name, type_def in schema.type_map.items():
        # Skip built-in types and non-object types
        if not isinstance(type_def, GraphQLObjectType) or type_name.startswith("__"):
            continue

        meta = type_metadata.get(type_name, {})
        _metadata = meta.get("metadata", {})
        # Skip types without a db_table metadata key
        if "db_table" not in _metadata:
            continue

        model_class = create_model_class(
            type_name,
            type_def.fields,
            meta,
            field_metadata.get(type_name, {}),
        )
        model_classes.append(model_class)

    # Create the module
    module = ast.Module(
        body=imports + [base_class] + model_classes,  # type: ignore
        type_ignores=[],
    )

    # Fix missing locations
    fixed_module = fix_missing_locations(module)

    return fixed_module
