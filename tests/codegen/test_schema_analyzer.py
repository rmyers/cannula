from typing import Dict, Any, Optional
from graphql import GraphQLObjectType

from cannula.codegen.schema_analyzer import ObjectType
from cannula.types import SQLMetadata


# Helper function to create GraphQLObjectType for testing
def create_graphql_type(
    name: str,
    extensions: Optional[Dict[str, Any]] = None,
    description: Optional[str] = None,
) -> GraphQLObjectType:
    return GraphQLObjectType(
        name=name,
        fields={},
        extensions=extensions or {},
        description=description,
    )


def test_typeinfo_full_initialization():
    """Test full initialization of TypeInfo with all fields"""
    type_def = create_graphql_type(
        name="User",
        extensions={"sql_metadata": SQLMetadata(table_name="users")},
        description="A user in the system",
    )

    type_info = ObjectType(
        type_def=type_def,
        name="User",
        py_type="UserType",
        fields=[],
    )

    assert type_info.type_def == type_def
    assert type_info.name == "User"
    assert type_info.py_type == "UserType"
    assert type_info.fields == []
    assert type_info.description == "A user in the system"
    assert type_info.is_db_type is True
    assert type_info.db_type == "DBUser"
    assert type_info.context_attr == "users"
