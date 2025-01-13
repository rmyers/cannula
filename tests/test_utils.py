from __future__ import annotations
import pytest
from textwrap import dedent
from typing import Union

from cannula import utils


def test_gql():
    schema = utils.gql("type Foo { id: Int }")
    assert schema.to_dict() == {
        "definitions": [
            {
                "description": None,
                "directives": [],
                "fields": [
                    {
                        "arguments": [],
                        "description": None,
                        "directives": [],
                        "kind": "field_definition",
                        "name": {"kind": "name", "value": "id"},
                        "type": {
                            "kind": "named_type",
                            "name": {"kind": "name", "value": "Int"},
                        },
                    }
                ],
                "interfaces": [],
                "kind": "object_type_definition",
                "name": {"kind": "name", "value": "Foo"},
            }
        ],
        "kind": "document",
    }


@pytest.mark.parametrize(
    "description,expected",
    [
        pytest.param(
            "Simple description\n@metadata(foo: bar)",
            dedent(
                """\
                Simple description
                ---
                metadata:
                  foo: bar"""
            ),
            id="basic_single_metadata",
        ),
        pytest.param(
            "Complex description\n@metadata(foo: bar, index: true, count: 42)",
            dedent(
                """\
                Complex description
                ---
                metadata:
                  foo: bar
                  index: true
                  count: 42"""
            ),
            id="multiple_metadata_fields",
        ),
        pytest.param(
            "Testing no spaces\n@metadata(foo:bar, index:true)",
            dedent(
                """\
                Testing no spaces
                ---
                metadata:
                  foo: bar
                  index: true"""
            ),
            id="no_spaces_after_colons",
        ),
        pytest.param(
            "Special chars\n@metadata(name: special:value, path: /foo/bar)",
            dedent(
                """\
                Special chars
                ---
                metadata:
                  name: "special:value"
                  path: "/foo/bar\""""
            ),
            id="special_characters_requiring_quotes",
        ),
        pytest.param(
            "Mixed types\n@metadata(str: value, num: 123, float: 45.67, bool: true)",
            dedent(
                """\
                Mixed types
                ---
                metadata:
                  str: value
                  num: 123
                  float: 45.67
                  bool: true"""
            ),
            id="mixed_value_types",
        ),
        pytest.param("Just a description", "Just a description", id="no_metadata"),
        pytest.param(
            "Empty metadata\n@metadata()",
            dedent(
                """\
                Empty metadata
                ---
                metadata:"""
            ),
            id="empty_metadata",
        ),
    ],
)
def test_parse_metadata_to_yaml(description: str, expected: str):
    result = utils.parse_metadata_to_yaml(description)
    assert result == expected


@pytest.mark.parametrize(
    "metadata_str,expected",
    [
        pytest.param(
            "foo: bar, num: 42",
            {"foo": "bar", "num": 42},
            id="basic_key_value_pairs",
        ),
        pytest.param(
            "active: true, disabled: false",
            {"active": True, "disabled": False},
            id="boolean_values",
        ),
        pytest.param(
            "foo:bar, num:42",
            {"foo": "bar", "num": 42},
            id="no_spaces_after_colons",
        ),
        pytest.param(
            "str: value, num: 123, float: 45.67, bool: true",
            {"str": "value", "num": 123, "float": 45.67, "bool": True},
            id="mixed_types",
        ),
        pytest.param("", {}, id="empty"),
        pytest.param("foo: bar", {"foo": "bar"}, id="single"),
    ],
)
def test_parse_metadata_pairs(metadata_str: str, expected: dict):
    result = utils.parse_metadata_pairs(metadata_str)
    assert result == expected


@pytest.mark.parametrize(
    "value,expected",
    [
        pytest.param("simple", False, id="simple_string"),
        pytest.param("special:value", True, id="contains_colon"),
        pytest.param("path/with/slashes", True, id="contains_slashes"),
        pytest.param("contains spaces", True, id="contains_spaces"),
        pytest.param("has[brackets]", True, id="contains_brackets"),
        pytest.param("has{braces}", True, id="contains_braces"),
        pytest.param("has#hash", True, id="contains_hash"),
        pytest.param("", False, id="empty_string"),
        pytest.param("  ", True, id="only_whitespace"),
        pytest.param("true", False, id="yaml_true_keyword"),
        pytest.param("false", False, id="yaml_false_keyword"),
        pytest.param("null", False, id="yaml_null_keyword"),
        pytest.param("1234", False, id="numeric_string"),
    ],
)
def test_need_quotes(value: str, expected: bool):
    result = utils.need_quotes(value)
    assert result == expected


@pytest.mark.parametrize(
    "value,expected",
    [
        pytest.param("simple", "simple", id="simple_string"),
        pytest.param('quoted"value"here', 'quoted"value"here', id="quoted_string"),
        pytest.param("true", True, id="boolean_true"),
        pytest.param("false", False, id="boolean_false"),
        pytest.param("True", True, id="boolean_true_capital"),
        pytest.param("False", False, id="boolean_false_capital"),
        pytest.param("123", 123, id="integer"),
        pytest.param("45.67", 45.67, id="float"),
        pytest.param("0", 0, id="zero"),
        pytest.param("", "", id="empty_string"),
        pytest.param("null", "null", id="null_string"),
    ],
)
def test_parse_value(value: str, expected: Union[str, bool, int, float]):
    result = utils.parse_value(value)
    assert result == expected


@pytest.mark.parametrize(
    "name, expected_plural",
    [
        # Regular plurals
        ("User", "users"),
        ("Book", "books"),
        # Sibilant endings (s, sh, ch, x, z)
        ("Class", "classes"),
        ("Bush", "bushes"),
        ("Match", "matches"),
        ("Box", "boxes"),
        ("Quiz", "quizzes"),
        ("Buzz", "buzzes"),
        # Words ending in y
        ("City", "cities"),  # consonant + y
        ("Day", "days"),  # vowel + y
        ("Boy", "boys"),  # vowel + y
        # Words ending in f/fe
        ("Wolf", "wolves"),
        ("Knife", "knives"),
        ("Life", "lives"),
        # Words ending in o
        ("Hero", "heroes"),
        ("Potato", "potatoes"),
        ("Studio", "studios"),
        ("Radio", "radios"),
        ("Video", "videos"),
        # Latin/Greek endings
        ("Analysis", "analyses"),
        ("Basis", "bases"),
        ("Focus", "foci"),
        ("Stimulus", "stimuli"),
        ("Criterion", "criteria"),
        ("Phenomenon", "phenomena"),
        # Irregular plurals
        ("Person", "people"),
        ("Child", "children"),
        ("Mouse", "mice"),
        ("Goose", "geese"),
        # Edge cases
        (
            "Data",
            "datas",
        ),  # Technically "data" is already plural, but in GraphQL we might want to treat it as singular
        ("Schema", "schemas"),  # Both "schemas" and "schemata" are valid
    ],
)
def test_context_attr_pluralization(name: str, expected_plural: str):
    actual = utils.pluralize(name)
    assert actual == expected_plural
