"""
This is just a simple in memory session for storing our logged in users.

Not really production worthy, just an example of using a session. It is just
a dict. Nothing fancy going on here. It lives in this module so that we can
avoid circular imports.
"""
import typing
import uuid

SESSION = {}


class User(typing.NamedTuple):
    catalog: dict
    auth_token: str
    username: str
    session_id: str


def get_user(session_id: str) -> User:
    return SESSION.get(session_id)


def set_user(catalog: dict, auth_token: str, username: str) -> User:
    session_id = str(uuid.uuid4())
    user = User(catalog, auth_token, username, session_id)
    SESSION[session_id] = user
    return user
