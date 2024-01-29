import uuid
import typing

from dashboard.core.database import User, users

# Global session store
SESSION: typing.Dict[uuid.UUID, User] = {}


async def signin(email: str, password: str) -> uuid.UUID:
    """Sign a user in and save the user info in the session store.

    Returns:
        uuid - id of the session object
    """
    if user := await users.get(email=email):
        if user.password == password:
            session_id = uuid.uuid4()
            SESSION[session_id] = user
            return session_id

    raise Exception("Invalid email or password")
