import cannula
from fastapi import Request
from sqlalchemy.ext.asyncio import async_sessionmaker


class Context(cannula.Context):
    """
    This context is added by the fastapi dependency, here we initialize
    the context with our database session maker and anything else.
    This allows us to pass data down to the resolvers from the original
    request and anything else we want to share.
    """

    session: async_sessionmaker
    authorization: str | None

    def __init__(self, session: async_sessionmaker, request: Request) -> None:
        self.session = session
        self.request = request
        self.authorization = request.headers.get("Authorization")
