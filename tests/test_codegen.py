import ast
import tempfile
import pathlib

import pytest

from cannula.codegen import parse_schema, render_file, render_object
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
import cannula
from pydantic import BaseModel
from typing import Awaitable, List, Optional, Protocol, TypedDict, Union
from typing_extensions import NotRequired


class EmailSearchTypeBase(BaseModel):
    __typename = "EmailSearch"
    email: str
    limit: Optional[int] = 100
    other: Optional[str] = "blah"
    include: Optional[bool] = False


class EmailSearchTypeDict(TypedDict):
    email: str
    limit: NotRequired[int]
    other: NotRequired[str]
    include: NotRequired[bool]


EmailSearchType = Union[EmailSearchTypeBase, EmailSearchTypeDict]


class MessageTypeBase(BaseModel):
    __typename = "Message"
    text: Optional[str] = None
    sender: Optional[SenderType] = None


class MessageTypeDict(TypedDict):
    text: NotRequired[str]
    sender: NotRequired[SenderType]


MessageType = Union[MessageTypeBase, MessageTypeDict]


class SenderTypeBase(BaseModel):
    __typename = "Sender"
    name: Optional[str] = None
    email: str


class SenderTypeDict(TypedDict):
    name: NotRequired[str]
    email: str


SenderType = Union[SenderTypeBase, SenderTypeDict]


class get_sender_by_emailQuery(Protocol):
    def __call__(
        self, info: cannula.ResolveInfo, *, input: Optional[EmailSearchType] = None
    ) -> Awaitable[SenderType]: ...


class messageMutation(Protocol):
    def __call__(
        self, info: cannula.ResolveInfo, text: str, sender: str
    ) -> Awaitable[MessageType]: ...


class messagesQuery(Protocol):
    def __call__(
        self, info: cannula.ResolveInfo, limit: int
    ) -> Awaitable[List[MessageType]]: ...


class RootType(TypedDict):
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
        with open(generated_file.name, "r") as rendered:
            content = rendered.read()

            assert content == expected


EXPECTED_OBJECT = """\
Module(
    body=[
        ClassDef(
            name='TestTypeBase',
            bases=[
                Name(id='BaseModel', ctx=Load())],
            keywords=[],
            body=[
                Assign(
                    targets=[
                        Name(id='__typename', ctx=Load())],
                    value=Constant(value='Test')),
                FunctionDef(
                    name='name',
                    args=arguments(
                        posonlyargs=[],
                        args=[
                            arg(arg='self'),
                            arg(
                                arg='info',
                                annotation=Name(id='cannula.ResolveInfo', ctx=Load()))],
                        kwonlyargs=[],
                        kw_defaults=[],
                        defaults=[]),
                    body=[
                        Pass()],
                    decorator_list=[
                        Name(id='abc.abstractmethod', ctx=Load())],
                    returns=Name(id='Awaitable[Optional[str]]', ctx=Load()))],
            decorator_list=[]),
        ClassDef(
            name='TestTypeDict',
            bases=[
                Name(id='TypedDict', ctx=Load())],
            keywords=[],
            body=[
                AnnAssign(
                    target=Name(id='name', ctx=Store()),
                    annotation=Name(id='NotRequired[str]', ctx=Load()),
                    simple=1)],
            decorator_list=[]),
        Assign(
            targets=[
                Name(id='TestType', ctx=Load())],
            value=Subscript(
                value=Name(id='Union', ctx=Load()),
                slice=Tuple(
                    elts=[
                        Name(id='TestTypeBase', ctx=Load()),
                        Name(id='TestTypeDict', ctx=Load())],
                    ctx=Load()),
                ctx=Load()))],
    type_ignores=[])\
"""


async def test_render_object_handles_computed_directive():
    schema = "type Test { name: String @computed}"
    actual = parse_schema([schema])

    assert actual is not None
    obj = actual["Test"]
    rendered = render_object(obj)
    root = ast.Module(body=rendered, type_ignores=[])
    assert ast.dump(root, indent=4) == EXPECTED_OBJECT
