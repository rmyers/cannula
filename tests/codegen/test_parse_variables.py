import pytest
from graphql import (
    ListTypeNode,
    NamedTypeNode,
    NonNullTypeNode,
    VariableNode,
    NameNode,
    VariableDefinitionNode,
)
from cannula.codegen.parse_variables import (
    parse_variable,
    Variable,
)


@pytest.mark.parametrize(
    "variable_def,expected",
    [
        pytest.param(
            VariableDefinitionNode(
                variable=VariableNode(name=NameNode(value="id")),
                type=NamedTypeNode(name=NameNode(value="ID")),
            ),
            Variable(name="id", value="ID", required=False, is_list=False),
            id="basic_id_type",
        ),
        pytest.param(
            VariableDefinitionNode(
                variable=VariableNode(name=NameNode(value="name")),
                type=NonNullTypeNode(type=NamedTypeNode(name=NameNode(value="String"))),
            ),
            Variable(name="name", value="String", required=True, is_list=False),
            id="required_string_type",
        ),
        pytest.param(
            VariableDefinitionNode(
                variable=VariableNode(name=NameNode(value="numbers")),
                type=ListTypeNode(type=NamedTypeNode(name=NameNode(value="Int"))),
            ),
            Variable(name="numbers", value="Int", required=False, is_list=True),
            id="list_of_integers",
        ),
        pytest.param(
            VariableDefinitionNode(
                variable=VariableNode(name=NameNode(value="tags")),
                type=NonNullTypeNode(
                    type=ListTypeNode(
                        type=NonNullTypeNode(
                            type=NamedTypeNode(name=NameNode(value="String"))
                        )
                    )
                ),
            ),
            Variable(name="tags", value="String", required=True, is_list=True),
            id="required_list_of_required_strings",
        ),
    ],
)
def test_parse_variable(variable_def, expected):
    result = parse_variable(variable_def)
    assert result == expected


@pytest.mark.parametrize(
    "variable,input_value,expected",
    [
        pytest.param(
            Variable(name="age", value="Int", required=True, is_list=False),
            "25",
            25,
            id="coerce_integer",
        ),
        pytest.param(
            Variable(name="price", value="Float", required=False, is_list=False),
            "99.99",
            99.99,
            id="coerce_float",
        ),
        pytest.param(
            Variable(name="active", value="Boolean", required=True, is_list=False),
            "true",
            True,
            id="coerce_boolean_true",
        ),
        pytest.param(
            Variable(name="active", value="Boolean", required=True, is_list=False),
            "YES",
            True,
            id="coerce_boolean_yes",
        ),
        pytest.param(
            Variable(name="active", value="Boolean", required=True, is_list=False),
            "1",
            True,
            id="coerce_boolean_one",
        ),
        pytest.param(
            Variable(name="id", value="ID", required=True, is_list=False),
            "123",
            "123",
            id="coerce_id",
        ),
        pytest.param(
            Variable(name="name", value="String", required=True, is_list=False),
            "test",
            "test",
            id="coerce_string",
        ),
    ],
)
def test_variable_coerce(variable, input_value, expected):
    result = variable.coerce_variable(input_value)
    assert result == expected


def test_invalid_type(mocker):
    class InvalidTypeNode:
        variable = mocker.Mock()
        default_value = None
        type = mocker.Mock()

    with pytest.raises(AttributeError, match="unable to parse variable"):
        parse_variable(
            InvalidTypeNode(),  # type: ignore
        )
