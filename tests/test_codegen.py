import ast
import tempfile
import pathlib

import pytest

from cannula.codegen import parse_schema, render_file, render_object
from cannula.types import Argument, Directive, Field
from cannula.scalars import ScalarInterface
from cannula.scalars.date import Datetime

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
from abc import ABC
from cannula import ResolveInfo
from dataclasses import dataclass
from typing import List, Optional, Protocol, Union
from typing_extensions import TypedDict


@dataclass(kw_only=True)
class EmailSearchTypeBase(ABC):
    __typename = "EmailSearch"
    email: str
    limit: Optional[int] = 100
    other: Optional[str] = "blah"
    include: Optional[bool] = False


class EmailSearchTypeDict(TypedDict, total=False):
    email: str
    limit: Optional[int]
    other: Optional[str]
    include: Optional[bool]


EmailSearchType = Union[EmailSearchTypeBase, EmailSearchTypeDict]


@dataclass(kw_only=True)
class MessageTypeBase(ABC):
    __typename = "Message"
    text: Optional[str] = None
    sender: Optional[SenderType] = None


class MessageTypeDict(TypedDict, total=False):
    text: Optional[str]
    sender: Optional[SenderType]


MessageType = Union[MessageTypeBase, MessageTypeDict]


@dataclass(kw_only=True)
class SenderTypeBase(ABC):
    __typename = "Sender"
    name: Optional[str] = None
    email: str


class SenderTypeDict(TypedDict, total=False):
    name: Optional[str]
    email: str


SenderType = Union[SenderTypeBase, SenderTypeDict]


class get_sender_by_emailQuery(Protocol):
    async def __call__(
        self, info: ResolveInfo, *, input: Optional[EmailSearchType] = None
    ) -> SenderType: ...


class messageMutation(Protocol):
    async def __call__(
        self, info: ResolveInfo, text: str, sender: str
    ) -> MessageType: ...


class messagesQuery(Protocol):
    async def __call__(self, info: ResolveInfo, limit: int) -> List[MessageType]: ...


class RootType(TypedDict, total=False):
    get_sender_by_email: Optional[get_sender_by_emailQuery]
    message: Optional[messageMutation]
    messages: Optional[messagesQuery]
"""

schema_interface = """\
scalar Datetime
interface Persona {
    id: ID!
}

type User implements Persona {
    id: ID!
}

type Admin implements Persona {
    id: ID!
    created: Datetime
}

union Person = User | Admin
"""

expected_interface = """\
from __future__ import annotations
from abc import ABC
from dataclasses import dataclass
from typing import Any, Optional, Protocol, Union
from typing_extensions import TypedDict

DatetimeType = Any


class PersonaType(Protocol):
    __typename = "Persona"
    id: str


@dataclass(kw_only=True)
class AdminTypeBase(ABC):
    __typename = "Admin"
    id: str
    created: Optional[DatetimeType] = None


class AdminTypeDict(TypedDict, total=False):
    id: str
    created: Optional[DatetimeType]


AdminType = Union[AdminTypeBase, AdminTypeDict]


@dataclass(kw_only=True)
class UserTypeBase(ABC):
    __typename = "User"
    id: str


class UserTypeDict(TypedDict, total=False):
    id: str


UserType = Union[UserTypeBase, UserTypeDict]
Person = Union[UserType, AdminType]
"""

schema_scalars = """\
scalar Datetime

type Thing {
    created: Datetime
}

input ThingMaker {
    created: Datetime!
}
"""

expected_scalars = """\
from __future__ import annotations
from abc import ABC
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Union
from typing_extensions import TypedDict


@dataclass(kw_only=True)
class ThingTypeBase(ABC):
    __typename = "Thing"
    created: Optional[datetime] = None


class ThingTypeDict(TypedDict, total=False):
    created: Optional[datetime]


ThingType = Union[ThingTypeBase, ThingTypeDict]


@dataclass(kw_only=True)
class ThingMakerTypeBase(ABC):
    __typename = "ThingMaker"
    created: datetime


class ThingMakerTypeDict(TypedDict, total=False):
    created: datetime


ThingMakerType = Union[ThingMakerTypeBase, ThingMakerTypeDict]
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
    "dry_run, schema, scalars, expected",
    [
        pytest.param(True, [SCHEMA, EXTENTIONS], [], "", id="dry-run:True"),
        pytest.param(
            False, [SCHEMA, EXTENTIONS], [], expected_output, id="dry-run:False"
        ),
        pytest.param(
            False, [schema_interface], [], expected_interface, id="interfaces"
        ),
        pytest.param(
            False,
            [schema_scalars],
            [Datetime],
            expected_scalars,
            id="scalars",
        ),
    ],
)
async def test_render_file(
    dry_run: bool, schema: list[str], expected: str, scalars: list[ScalarInterface]
):
    with tempfile.NamedTemporaryFile() as generated_file:
        render_file(
            schema,
            path=pathlib.Path(generated_file.name),
            dry_run=dry_run,
            scalars=scalars,
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
                Name(id='ABC', ctx=Load())],
            keywords=[],
            body=[
                Assign(
                    targets=[
                        Name(id='__typename', ctx=Load())],
                    value=Constant(value='Test')),
                AsyncFunctionDef(
                    name='name',
                    args=arguments(
                        posonlyargs=[],
                        args=[
                            arg(arg='self'),
                            arg(
                                arg='info',
                                annotation=Name(id='ResolveInfo', ctx=Load()))],
                        kwonlyargs=[],
                        kw_defaults=[],
                        defaults=[]),
                    body=[
                        Pass()],
                    decorator_list=[
                        Name(id='abstractmethod', ctx=Load())],
                    returns=Name(id='Optional[str]', ctx=Load()))],
            decorator_list=[
                Call(
                    func=Name(id='dataclass', ctx=Load()),
                    args=[],
                    keywords=[
                        keyword(
                            arg='kw_only',
                            value=Constant(value=True))])]),
        ClassDef(
            name='TestTypeDict',
            bases=[
                Name(id='TypedDict', ctx=Load())],
            keywords=[
                keyword(
                    arg='total',
                    value=Constant(value=False))],
            body=[
                AnnAssign(
                    target=Name(id='name', ctx=Store()),
                    annotation=Name(id='Optional[str]', ctx=Load()),
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
    root = ast.Module(body=[*rendered], type_ignores=[])
    assert ast.dump(root, indent=4) == EXPECTED_OBJECT
