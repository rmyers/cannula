import tempfile
import pathlib

import pytest

from cannula.codegen import parse_schema, render_file, Field


SCHEMA = '''
"""
Some sender action:

```
Sender(foo)
```
"""
type Sender {
    name: String @deprecated(reason: "Use `email`.")
}

type Message {
    text: String
    sender: Sender
}

type Query {
    messages(limit: Int): [Message]
}
'''

EXTENTIONS = """
    extend type Sender {
        email: String!
    }
    input EmailSearch {
        "email to search"
        email: String!
    }
    extend type Query {
        get_sender_by_email(input: EmailSearch): Sender
    }
"""

expected_output = """\
import typing
import dataclasses


Sender = dataclasses.make_dataclass(
    "Sender",
    fields=[
        (
            "name",
            typing.Optional[str],
            dataclasses.field(default=None)
        ),
        (
            "email",
            str,
        ),
    ],
)


Message = dataclasses.make_dataclass(
    "Message",
    fields=[
        (
            "text",
            typing.Optional[str],
            dataclasses.field(default=None)
        ),
        (
            "sender",
            typing.Optional["Sender"],
            dataclasses.field(default=None)
        ),
    ],
)


Query = dataclasses.make_dataclass(
    "Query",
    fields=[
        (
            "messages",
            typing.Optional[typing.List["Message"]],
            dataclasses.field(default=None)
        ),
        (
            "get_sender_by_email",
            typing.Optional["Sender"],
            dataclasses.field(default=None)
        ),
    ],
)


EmailSearch = dataclasses.make_dataclass(
    "EmailSearch",
    fields=[
        (
            "email",
            str,
        ),
    ],
)
"""


async def test_parse_schema_dict():
    schema = 'type Test { name: String @deprecated(reason: "not valid")}'
    actual = parse_schema([schema])

    assert actual is not None
    obj = actual["Test"]
    assert obj.name == "Test"
    assert obj.description is None
    assert obj.fields == [
        Field(
            name="name",
            value="str",
            description=None,
            default=None,
            required=False,
        )
    ]


@pytest.mark.parametrize(
    "dry_run, expected",
    [(True, ""), (False, expected_output)],
    ids=["dry-run:True", "dry-run:False"],
)
async def test_render_file(dry_run: bool, expected: str):
    with tempfile.NamedTemporaryFile() as generated_file:
        render_file(
            [SCHEMA, EXTENTIONS],
            path=pathlib.Path(generated_file.name),
            dry_run=dry_run,
        )
        with open(generated_file.name) as rendered:
            content = rendered.read()

            assert content == expected
