import tempfile
import pathlib

import pytest

from cannula.codegen import (
    render_file,
)
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

EXTENTIONS = """\
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

expected_output = '''\
from __future__ import annotations
from abc import ABC
from cannula import ResolveInfo
from dataclasses import dataclass
from typing import Optional, Protocol, Sequence
from typing_extensions import TypedDict


class EmailSearchInput(TypedDict):
    email: str
    limit: int
    other: str
    include: bool


@dataclass(kw_only=True)
class MessageType(ABC):
    __typename = "Message"
    text: Optional[str] = None
    sender: Optional[SenderType] = None


@dataclass(kw_only=True)
class SenderType(ABC):
    """
    Some sender action:

    ```
    Sender(foo)
    ```
    """

    __typename = "Sender"
    name: Optional[str] = None
    email: str


class get_sender_by_emailQuery(Protocol):

    async def __call__(
        self, info: ResolveInfo, *, input: Optional[EmailSearchInput] = None
    ) -> Optional[SenderType]: ...


class messageMutation(Protocol):

    async def __call__(
        self, info: ResolveInfo, sender: str, text: str
    ) -> Optional[MessageType]: ...


class messagesQuery(Protocol):

    async def __call__(
        self, info: ResolveInfo, limit: int
    ) -> Optional[Sequence[MessageType]]: ...


class RootType(TypedDict, total=False):
    get_sender_by_email: Optional[get_sender_by_emailQuery]
    message: Optional[messageMutation]
    messages: Optional[messagesQuery]
'''

expected_pydantic = '''\
from __future__ import annotations
from cannula import ResolveInfo
from pydantic import BaseModel
from typing import Optional, Protocol, Sequence
from typing_extensions import TypedDict


class EmailSearchInput(TypedDict):
    email: str
    limit: int
    other: str
    include: bool


class MessageType(BaseModel):
    __typename = "Message"
    text: Optional[str] = None
    sender: Optional[SenderType] = None


class SenderType(BaseModel):
    """
    Some sender action:

    ```
    Sender(foo)
    ```
    """

    __typename = "Sender"
    name: Optional[str] = None
    email: str


class get_sender_by_emailQuery(Protocol):

    async def __call__(
        self, info: ResolveInfo, *, input: Optional[EmailSearchInput] = None
    ) -> Optional[SenderType]: ...


class messageMutation(Protocol):

    async def __call__(
        self, info: ResolveInfo, sender: str, text: str
    ) -> Optional[MessageType]: ...


class messagesQuery(Protocol):

    async def __call__(
        self, info: ResolveInfo, limit: int
    ) -> Optional[Sequence[MessageType]]: ...


class RootType(TypedDict, total=False):
    get_sender_by_email: Optional[get_sender_by_emailQuery]
    message: Optional[messageMutation]
    messages: Optional[messagesQuery]
'''

schema_interface = """\
scalar Datetime
interface Persona {
    id: ID!
}

"Just a comment"
interface Other {
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

expected_interface = '''\
from __future__ import annotations
from abc import ABC
from dataclasses import dataclass
from typing import Any, Optional, Protocol, Union


class Other(Protocol):
    """Just a comment"""

    id: str


class Persona(Protocol):
    id: str


@dataclass(kw_only=True)
class AdminType(ABC):
    __typename = "Admin"
    id: str
    created: Optional[Any] = None


@dataclass(kw_only=True)
class UserType(ABC):
    __typename = "User"
    id: str


Person = Union[UserType, AdminType]
'''

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
from typing import Optional
from typing_extensions import TypedDict


class ThingMakerInput(TypedDict):
    created: datetime


@dataclass(kw_only=True)
class ThingType(ABC):
    __typename = "Thing"
    created: Optional[datetime] = None
"""


@pytest.mark.parametrize(
    "dry_run, schema, scalars, use_pydantic, expected",
    [
        pytest.param(
            True,
            [SCHEMA, EXTENTIONS],
            [],
            False,
            "",
            id="dry-run:True",
        ),
        pytest.param(
            False,
            [SCHEMA, EXTENTIONS],
            [],
            False,
            expected_output,
            id="dry-run:False",
        ),
        pytest.param(
            False,
            [schema_interface],
            [],
            False,
            expected_interface,
            id="interfaces",
        ),
        pytest.param(
            False,
            [schema_scalars],
            [Datetime],
            False,
            expected_scalars,
            id="scalars",
        ),
        pytest.param(
            False,
            [SCHEMA, EXTENTIONS],
            [Datetime],
            True,
            expected_pydantic,
            id="pydantic",
        ),
    ],
)
async def test_render_file(
    dry_run: bool,
    schema: list[str],
    scalars: list[ScalarInterface],
    use_pydantic: bool,
    expected: str,
):
    with tempfile.NamedTemporaryFile() as generated_file:
        render_file(
            type_defs=schema,
            dest=pathlib.Path(generated_file.name),
            dry_run=dry_run,
            scalars=scalars,
            use_pydantic=use_pydantic,
        )
        with open(generated_file.name, "r") as rendered:
            content = rendered.read()

            assert content == expected
