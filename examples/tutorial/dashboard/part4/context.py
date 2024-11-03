from functools import cached_property

import cannula
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

# This UserRepository follows the 'repository' pattern which encapsilates
# our database access so that we don't tightly couple our code to the db.
from ..core.repository import UserRepository


class Context(cannula.Context):
    """
    This context is added by the fastapi dependency, here we initialize
    the context with our database session and anything else. We use
    the session to setup our repositories and other dataloaders.
    """

    session: AsyncSession
    authorization: str | None

    def __init__(self, session: AsyncSession, request: Request) -> None:
        self.session = session
        self.authorization = request.headers.get("Authorization")

    @cached_property
    def user_repo(self) -> UserRepository:
        # Add this as a cached property so that we only initialize this
        # if we actually use it in a resolver
        return UserRepository(self.session)
