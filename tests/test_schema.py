import tempfile
import os
import pathlib

from graphql import (
    DocumentNode,
    parse,
    validate_schema,
)

import cannula

SCHEMA = """
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

EXTENTIONS = """
    extend type Sender {
        email: String
    }
    extend type Query {
        get_sender_by_email(email: String): Sender
    }
"""


async def get_sender_by_email(email: str) -> dict:
    return {"email": email, "name": "tester"}


async def test_extentions_are_correct():
    api = cannula.CannulaAPI(schema=SCHEMA + EXTENTIONS)

    @api.resolver("Query", "get_sender_by_email")
    async def get_sender_by_email(_root, _info, email: str) -> dict:
        return {"email": email, "name": "tester"}

    query = cannula.gql(
        """
        query Extentions {
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


async def test_extension_without_base_query():
    schema = cannula.gql("type Sender {name: String}")
    extended = cannula.build_and_extend_schema([schema, EXTENTIONS])
    errors = validate_schema(extended)
    assert errors == []


async def test_directives():
    document = parse('type Director { frank: String @cache(max: "50s") ted: String}')
    print(document.to_dict())
    parsed = document.to_dict()
    defs = parsed.get("definitions", [])
    # TODO get the directives to work
    assert len(defs[0].get("fields")) == 2


def test_load_schema_from_filename():
    with tempfile.NamedTemporaryFile(mode="w") as graph_schema:
        graph_schema.write(SCHEMA)
        graph_schema.seek(0)

        parsed = cannula.load_schema(graph_schema.name)
        assert len(parsed) == 1
        assert isinstance(parsed[0], DocumentNode)


def test_load_schema_from_pathlib_path():
    with tempfile.NamedTemporaryFile(mode="w") as graph_schema:
        graph_schema.write(SCHEMA)
        graph_schema.seek(0)

        parsed = cannula.load_schema(pathlib.Path(graph_schema.name))
        assert len(parsed) == 1
        assert isinstance(parsed[0], DocumentNode)


def test_load_schema_from_directory():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".graphql") as graph_schema:
        graph_schema.write(SCHEMA)
        graph_schema.seek(0)

        parsed = cannula.load_schema(os.path.dirname(graph_schema.name))
        assert len(parsed) == 1
        assert isinstance(parsed[0], DocumentNode)


def test_parse_schema_metadata_invalid_yaml():
    document = parse(
        '''
        """
        Invalid YAML metadata

        ---
        metadata:
            %@foo: bar
        """
        type Sender {
            name: String
        }
        '''
    )
    processor = cannula.SchemaProcessor()
    metadata = processor.process_schema(document)
    assert metadata.type_metadata["Sender"]["metadata"] == {}
    assert metadata.field_metadata["Sender"]["name"] == {
        "description": "",
        "metadata": {},
        "directives": [],
    }
