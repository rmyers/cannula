import pytest
from graphql import DocumentNode, parse, validate_schema
import cannula
import pathlib


@pytest.fixture
def base_schema() -> str:
    return """
    type Sender {
        name: String @deprecated(reason: "Use `email`.")
    }
    type Message {
        text: String
        sender: Sender
    }
    type Query {
        messages: [Message]
    }
    """


@pytest.fixture
def schema_extensions() -> str:
    return """
    extend type Sender {
        email: String
    }
    extend type Query {
        get_sender_by_email(email: String): Sender
    }
    """


@pytest.fixture
def schema_file(tmp_path, base_schema) -> pathlib.Path:
    schema_path = tmp_path / "schema.graphql"
    schema_path.write_text(base_schema)
    return schema_path


async def test_extensions_are_correct(base_schema, schema_extensions):
    api = cannula.CannulaAPI(schema=base_schema + schema_extensions)

    @api.resolver("Query", "get_sender_by_email")
    async def get_sender_by_email(_root, _info, email: str) -> dict:
        return {"email": email, "name": "tester"}

    query = cannula.gql(
        """
        query Extensions {
            get_sender_by_email(email: "test@example.com") {
                name
                email
            }
        }
        """
    )
    results = await api.call(query)
    assert results.data == {
        "get_sender_by_email": {
            "name": "tester",
            "email": "test@example.com",
        }
    }


async def test_extension_without_base_query(schema_extensions):
    schema = cannula.gql("type Sender {name: String}")
    extended = cannula.build_and_extend_schema([schema, schema_extensions])
    errors = validate_schema(extended)
    assert errors == []


async def test_directives():
    document = parse('type Director { frank: String @cache(max: "50s") ted: String}')
    parsed = document.to_dict()
    defs = parsed.get("definitions", [])
    # TODO get the directives to work
    assert len(defs[0].get("fields")) == 2


def test_load_schema_from_filename(schema_file):
    parsed = cannula.load_schema(schema_file)
    assert len(parsed) == 1
    assert isinstance(parsed[0], DocumentNode)


def test_load_schema_from_pathlib_path(schema_file):
    parsed = cannula.load_schema(pathlib.Path(schema_file))
    assert len(parsed) == 1
    assert isinstance(parsed[0], DocumentNode)


def test_load_schema_from_directory(tmp_path, base_schema, schema_extensions):
    # Create multiple schema files in different locations
    schema_file1 = tmp_path / "schema.graphql"
    schema_file1.write_text(base_schema)

    nested_dir = tmp_path / "nested"
    nested_dir.mkdir()
    schema_file2 = nested_dir / "extensions.graphql"
    schema_file2.write_text(schema_extensions)

    # Non-graphql file that should be ignored
    other_file = tmp_path / "other.txt"
    other_file.write_text("should be ignored")

    parsed = cannula.load_schema(tmp_path)
    assert len(parsed) == 2
    assert all(isinstance(doc, DocumentNode) for doc in parsed)


def test_load_schema_with_empty_directory(tmp_path):
    parsed = cannula.load_schema(tmp_path)
    assert len(parsed) == 0


def test_load_schema_with_str_path(schema_file):
    parsed = cannula.load_schema(str(schema_file))
    assert len(parsed) == 1
    assert isinstance(parsed[0], DocumentNode)


def test_load_schema_recursive_directory(tmp_path, base_schema):
    # Create a deeper nested directory structure
    level1 = tmp_path / "level1"
    level1.mkdir()
    level2 = level1 / "level2"
    level2.mkdir()

    schema_file = level2 / "nested_schema.graphql"
    schema_file.write_text(base_schema)

    parsed = cannula.load_schema(tmp_path)
    assert len(parsed) == 1
    assert isinstance(parsed[0], DocumentNode)
