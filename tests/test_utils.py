from __future__ import annotations
import pytest

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
