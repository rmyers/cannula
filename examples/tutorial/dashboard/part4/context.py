import cannula
from fastapi import Request
from sqlalchemy.ext.asyncio import async_sessionmaker


class Context(cannula.Context):
    """
    This context is added by the fastapi dependency, here we initialize
    the context with our database session and anything else. We use
    the session to setup our repositories and other dataloaders.
    """

    session: async_sessionmaker
    authorization: str | None

    def __init__(self, session: async_sessionmaker, request: Request) -> None:
        self.session = session
        self.authorization = request.headers.get("Authorization")
