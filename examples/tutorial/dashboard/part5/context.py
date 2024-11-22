import cannula
from sqlalchemy.ext.asyncio import async_sessionmaker

from .models import UserRepository, QuotaRepository


class Context(cannula.Context):
    """
    This context is added by the fastapi dependency, here we initialize
    the context with our database session makers and our repositories
    """

    def __init__(
        self,
        session: async_sessionmaker,
        readonly_session: async_sessionmaker | None = None,
    ) -> None:
        self.user_repo = UserRepository(session, readonly_session)
        self.quota_repo = QuotaRepository(session, readonly_session)
