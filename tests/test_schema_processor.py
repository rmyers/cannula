import typing
import pytest
from graphql import parse
from cannula.schema_processor import SchemaProcessor


def test_field_directive_parsing():
    schema_str = '''
    """Test type description"""
    type User {
        """Field with directives"""
        id: ID! @deprecated(reason: "Use uuid instead") @auth(requires: ["ADMIN"])

        """Another field"""
        name: String @length(min: 3, max: 50)
    }
    '''

    doc = parse(schema_str)
    processor = SchemaProcessor()
    metadata = processor.process_schema(doc)

    # Check User.id field directives
    id_metadata = metadata.field_metadata["User"]["id"]
    assert "directives" in id_metadata
    directives = id_metadata["directives"]
    assert len(directives) == 2

    # Check deprecated directive
    deprecated = next(d for d in directives if d.name == "deprecated")
    assert deprecated.args[0].name == "reason"
    assert deprecated.args[0].value == "Use uuid instead"

    # Check auth directive
    auth = next(d for d in directives if d.name == "auth")
    assert auth.args[0].name == "requires"
    assert auth.args[0].value == ["ADMIN"]

    # Check name field directive
    name_metadata = metadata.field_metadata["User"]["name"]
    length_directive = name_metadata["directives"][0]
    assert length_directive.name == "length"
    assert len(length_directive.args) == 2
    assert {arg.name: arg.value for arg in length_directive.args} == {
        "min": 3,
        "max": 50,
    }


def test_field_without_directives():
    schema_str = """
    type Simple {
        basic: String
    }
    """

    doc = parse(schema_str)
    processor = SchemaProcessor()
    metadata = processor.process_schema(doc)

    field_metadata = metadata.field_metadata["Simple"]["basic"]
    assert "directives" in field_metadata
    assert field_metadata["directives"] == []


@pytest.mark.parametrize(
    "directive_str,expected_args",
    [
        pytest.param('@test(str: "value")', [("str", "value")], id="string-arg"),
        pytest.param("@test(num: 42)", [("num", 42)], id="int-arg"),
        pytest.param("@test(flag: true)", [("flag", True)], id="bool-arg"),
        pytest.param("@test(list: [1, 2, 3])", [("list", [1, 2, 3])], id="list-arg"),
        pytest.param(
            '@test(multiple: true, name: "test")',
            [("multiple", True), ("name", "test")],
            id="multiple-args",
        ),
    ],
)
def test_directive_argument_parsing(
    directive_str: str, expected_args: list[tuple[str, typing.Any]]
):
    schema_str = f"""
    type Test {{
        field: String {directive_str}
    }}
    """

    doc = parse(schema_str)
    processor = SchemaProcessor()
    metadata = processor.process_schema(doc)

    directives = metadata.field_metadata["Test"]["field"]["directives"]
    assert len(directives) == 1
    directive = directives[0]
    assert directive.name == "test"

    arg_dict = {arg.name: arg.value for arg in directive.args}
    assert arg_dict == dict(expected_args)
