from __future__ import annotations
import collections
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


def test_find_package_root_basic(tmp_path):
    # Create pyproject.toml in tmp directory
    (tmp_path / "pyproject.toml").touch()

    # Test finding from a nested directory
    nested_dir = tmp_path / "src" / "package" / "submodule"
    nested_dir.mkdir(parents=True)

    result = utils.find_package_root(nested_dir)
    assert result == tmp_path


def test_find_package_root_max_depth(tmp_path):
    # Create deep nested structure without markers
    deep_path = tmp_path
    for i in range(6):
        deep_path = deep_path / f"level_{i}"
        deep_path.mkdir()

    # Create marker file beyond max_depth
    (tmp_path / "pyproject.toml").touch()

    with pytest.raises(utils.ProjectRootError) as exc_info:
        utils.find_package_root(deep_path, max_depth=3)

    assert "Could not find project root" in str(exc_info.value)
    assert "within 3 levels" in str(exc_info.value)


def test_find_package_root_no_markers(tmp_path):
    nested_dir = tmp_path / "src" / "package"
    nested_dir.mkdir(parents=True)

    with pytest.raises(utils.ProjectRootError) as exc_info:
        utils.find_package_root(nested_dir)

    assert "Could not find project root" in str(exc_info.value)


def test_find_package_root_skips_internal(tmp_path, monkeypatch):
    # Create dummy internal file paths that should be skipped
    def mock_stack():
        Frame = collections.namedtuple("Frame", ["filename"])
        return [
            Frame(filename="cannula/utils.py"),
            Frame(filename="cannula/api.py"),
            Frame(filename=str(tmp_path / "user_code.py")),
        ]

    monkeypatch.setattr("inspect.stack", mock_stack)

    # Create marker file
    (tmp_path / "pyproject.toml").touch()

    result = utils.find_package_root()
    assert result == tmp_path


@pytest.mark.parametrize(
    "config, expected",
    [
        pytest.param("$config.bar", "bar", id="defualt"),
        pytest.param(None, None, id="none"),
        pytest.param("$config.", None, id="missing"),
    ],
)
def test_get_config_var(config, expected):
    actual = utils.get_config_var(config)
    assert actual == expected
