import tempfile
import pathlib

import pytest

from cannula.codegen import parse_schema, render_file
from cannula.types import Argument, Directive, Field


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
    messages(limit: Int!): [Message]
}

type Mutation {
    message(text: String!, sender: String!): Message
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

import abc
import dataclasses
import typing

from typing_extensions import NotRequired

import cannula


@dataclasses.dataclass
class EmailSearchTypeBase(abc.ABC):
    __typename = "EmailSearch"

    email: str
    limit: typing.Optional[int] = 100
    other: typing.Optional[str] = 'blah'
    include: typing.Optional[bool] = False


class EmailSearchTypeDict(typing.TypedDict):
    email: str
    limit: NotRequired[int]
    other: NotRequired[str]
    include: NotRequired[bool]


EmailSearchType = typing.Union[EmailSearchTypeBase, EmailSearchTypeDict]


@dataclasses.dataclass
class MessageTypeBase(abc.ABC):
    __typename = "Message"

    text: typing.Optional[str] = None
    sender: typing.Optional[SenderType] = None


class MessageTypeDict(typing.TypedDict):
    text: NotRequired[str]
    sender: NotRequired[SenderType]


MessageType = typing.Union[MessageTypeBase, MessageTypeDict]


@dataclasses.dataclass
class SenderTypeBase(abc.ABC):
    __typename = "Sender"

    name: typing.Optional[str] = None
    email: str


class SenderTypeDict(typing.TypedDict):
    name: NotRequired[str]
    email: str


SenderType = typing.Union[SenderTypeBase, SenderTypeDict]


class get_sender_by_emailQuery(typing.Protocol):
    def __call__(
        self,
        info: cannula.ResolveInfo,
        input: typing.Optional[EmailSearchType] = None,
    ) -> typing.Awaitable[SenderType]:
        ...


class messageMutation(typing.Protocol):
    def __call__(
        self,
        info: cannula.ResolveInfo,
        text: str,
        sender: str,
    ) -> typing.Awaitable[MessageType]:
        ...


class messagesQuery(typing.Protocol):
    def __call__(
        self,
        info: cannula.ResolveInfo,
        limit: int,
    ) -> typing.Awaitable[typing.List[MessageType]]:
        ...


class RootType(typing.TypedDict):
    get_sender_by_email: NotRequired[get_sender_by_emailQuery]
    message: NotRequired[messageMutation]
    messages: NotRequired[messagesQuery]
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
                    args=[Argument(name="reason", value="not valid", default=None)],
                ),
            ],
            args=[],
            func_name="nameTest",
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
