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
from typing import Optional, Protocol, Sequence, TYPE_CHECKING
from typing_extensions import TypedDict

if TYPE_CHECKING:
    from .context import Context


class EmailSearch(TypedDict):
    email: str
    limit: int
    other: str
    include: bool


@dataclass(kw_only=True)
class Message(ABC):
    __typename = "Message"
    text: Optional[str] = None

    async def sender(self, info: ResolveInfo["Context"]) -> Optional[Sender]:
        return await info.context.senders.message_sender()


@dataclass(kw_only=True)
class Sender(ABC):
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
        self, info: ResolveInfo["Context"], *, input: Optional[EmailSearch] = None
    ) -> Optional[Sender]: ...


class messageMutation(Protocol):

    async def __call__(
        self, info: ResolveInfo["Context"], sender: str, text: str
    ) -> Optional[Message]: ...


class messagesQuery(Protocol):

    async def __call__(
        self, info: ResolveInfo["Context"], limit: int
    ) -> Optional[Sequence[Message]]: ...


class RootType(TypedDict, total=False):
    get_sender_by_email: Optional[get_sender_by_emailQuery]
    message: Optional[messageMutation]
    messages: Optional[messagesQuery]
'''

expected_pydantic = '''\
from __future__ import annotations
from cannula import ResolveInfo
from pydantic import BaseModel
from typing import Optional, Protocol, Sequence, TYPE_CHECKING
from typing_extensions import TypedDict

if TYPE_CHECKING:
    from .context import Context


class EmailSearch(TypedDict):
    email: str
    limit: int
    other: str
    include: bool


class Message(BaseModel):
    __typename = "Message"
    text: Optional[str] = None

    async def sender(self, info: ResolveInfo["Context"]) -> Optional[Sender]:
        return await info.context.senders.message_sender()


class Sender(BaseModel):
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
        self, info: ResolveInfo["Context"], *, input: Optional[EmailSearch] = None
    ) -> Optional[Sender]: ...


class messageMutation(Protocol):

    async def __call__(
        self, info: ResolveInfo["Context"], sender: str, text: str
    ) -> Optional[Message]: ...


class messagesQuery(Protocol):

    async def __call__(
        self, info: ResolveInfo["Context"], limit: int
    ) -> Optional[Sequence[Message]]: ...


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
from typing import Any, Optional, Protocol, TYPE_CHECKING, Union

if TYPE_CHECKING:
    pass


class Other(Protocol):
    """Just a comment"""

    id: str


class Persona(Protocol):
    id: str


@dataclass(kw_only=True)
class Admin(ABC):
    __typename = "Admin"
    id: str
    created: Optional[Any] = None


@dataclass(kw_only=True)
class User(ABC):
    __typename = "User"
    id: str


Person = Union[User, Admin]
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
from typing import Optional, TYPE_CHECKING
from typing_extensions import TypedDict

if TYPE_CHECKING:
    pass


class ThingMaker(TypedDict):
    created: datetime


@dataclass(kw_only=True)
class Thing(ABC):
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
    with tempfile.TemporaryDirectory() as generated_dir:
        destination = pathlib.Path(generated_dir)
        render_file(
            type_defs=schema,
            dest=destination,
            dry_run=dry_run,
            scalars=scalars,
            use_pydantic=use_pydantic,
        )
        if dry_run:
            assert not (destination / "types.py").exists()
            return

        with open(destination / "types.py", "r") as rendered:
            content = rendered.read()

            assert content == expected
