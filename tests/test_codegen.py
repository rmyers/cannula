import tempfile
import pathlib

import pytest

from cannula.codegen import parse_schema, render_file, Field, Directive


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
        limit: Int = 100
        other: String = "blah"
        include: Boolean = false
    }
    extend type Query {
        get_sender_by_email(input: EmailSearch): Sender
    }
"""

expected_output = """\
from __future__ import annotations

import typing
import dataclasses


@dataclasses.dataclass
class Directive:
    name: str
    args: typing.Dict[str, typing.Any]


DirectiveType = typing.Dict[str, typing.List[Directive]]


@dataclasses.dataclass
class SenderType:
    __typename = "Sender"
    __directives__: DirectiveType = {'name': [Directive(name='deprecated', args={'reason': 'Use `email`.'})]}

    name: typing.Optional[str] = None
    email: str


@dataclasses.dataclass
class MessageType:
    __typename = "Message"
    __directives__: DirectiveType = {}

    text: typing.Optional[str] = None
    sender: typing.Optional[SenderType] = None


@dataclasses.dataclass
class QueryType:
    __typename = "Query"
    __directives__: DirectiveType = {}

    messages: typing.Optional[typing.List[MessageType]] = None
    get_sender_by_email: typing.Optional[SenderType] = None


@dataclasses.dataclass
class EmailSearchType:
    __typename = "EmailSearch"
    __directives__: DirectiveType = {}

    email: str
    limit: typing.Optional[int] = 100
    other: typing.Optional[str] = 'blah'
    include: typing.Optional[bool] = False
"""


async def test_parse_schema_dict():
    schema = 'type Test { "name field" name: String @deprecated(reason: "not valid")}'
    actual = parse_schema([schema])

    assert actual is not None
    obj = actual["Test"]
    assert obj.name == "Test"
    assert obj.description is None
    assert obj.fields == [
        Field(
            name="name",
            value="str",
            description="name field",
            directives=[
                Directive(
                    name="deprecated",
                    args={"reason": "not valid"},
                ),
            ],
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
