import pytest
from typing import Dict, Any, Optional
from graphql import GraphQLObjectType

from cannula.codegen.schema_analyzer import ObjectType


# Helper function to create GraphQLObjectType for testing
def create_graphql_type(
    name: str, extensions: Optional[Dict[str, Any]] = None
) -> GraphQLObjectType:
    return GraphQLObjectType(name=name, fields={}, extensions=extensions or {})


@pytest.mark.parametrize(
    "name,py_type,metadata,expected_is_db_type",
    [
        ("User", "User", {}, False),
        ("User", "User", {"db_table": "users"}, True),
        ("Post", "Post", {"db_table": False}, False),
        ("Comment", "Comment", {"db_table": True}, True),
    ],
)
def test_is_db_type(
    name: str, py_type: str, metadata: Dict[str, Any], expected_is_db_type: bool
):
    type_def = create_graphql_type(name=name)
    type_info = ObjectType(
        type_def=type_def, name=name, py_type=py_type, metadata=metadata, fields=[]
    )
    assert type_info.is_db_type == expected_is_db_type


@pytest.mark.parametrize(
    "name,type_extensions,expected_db_type",
    [
        ("User", {}, "DBUser"),
        ("User", {"db_type": "UserModel"}, "UserModel"),
        ("Post", {"db_type": "PostEntity"}, "PostEntity"),
        ("Comment", {}, "DBComment"),
    ],
)
def test_db_type(name: str, type_extensions: Dict[str, Any], expected_db_type: str):
    type_def = create_graphql_type(name=name, extensions=type_extensions)
    type_info = ObjectType(
        type_def=type_def, name=name, py_type=name, metadata={}, fields=[]
    )
    assert type_info.db_type == expected_db_type


def test_typeinfo_full_initialization():
    """Test full initialization of TypeInfo with all fields"""
    type_def = create_graphql_type(name="User")

    type_info = ObjectType(
        type_def=type_def,
        name="User",
        py_type="UserType",
        metadata={"db_table": "users"},
        fields=[],
        description="A user in the system",
    )

    assert type_info.type_def == type_def
    assert type_info.name == "User"
    assert type_info.py_type == "UserType"
    assert type_info.metadata == {"db_table": "users"}
    assert type_info.fields == []
    assert type_info.description == "A user in the system"
    assert type_info.is_db_type is True
    assert type_info.db_type == "DBUser"
    assert type_info.context_attr == "users"
