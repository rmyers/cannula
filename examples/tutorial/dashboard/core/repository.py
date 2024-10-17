import uuid
from typing import Any, Dict, Generic, Optional, TypeVar

from sqlalchemy import BinaryExpression, ColumnExpressionArgument, select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from .database import Base, User

Model = TypeVar("Model", bound=Base)
GraphQLModel = TypeVar("GraphQLModel")

# Global session store
SESSION: Dict[str, User] = {}


class DBMixin(Generic[Model, GraphQLModel]):
    """Used to map a database model to a generated GraphQL type"""

    _db_model: Model

    @classmethod
    def from_db(cls, db_obj: Model) -> GraphQLModel:
        obj = cls(**db_obj.__dict__)
        obj._db_model = db_obj
        return obj  # type: ignore


class DatabaseRepository(Generic[Model]):
    """Repository for performing database queries."""

    def __init__(self, model: type[Model], session: AsyncSession) -> None:
        self.model = model
        self.session = session

    async def add(self, **data: Any) -> Model:
        instance = self.model(**data)
        self.session.add(instance)
        await self.session.commit()
        await self.session.refresh(instance)
        return instance

    async def get(self, pk: uuid.UUID) -> Model | None:
        return await self.session.get(self.model, pk)

    async def filter(
        self,
        *expressions: BinaryExpression | ColumnExpressionArgument,
    ) -> list[Model]:
        query = select(self.model)
        if expressions:
            query = query.where(*expressions)
        return list(await self.session.scalars(query))


class UserRepository(DatabaseRepository[User]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(User, session)

    async def add(
        self,
        name: str,
        email: str,
        password: str,
        id: Optional[uuid.UUID] = None,
    ) -> User:
        is_admin = "admin" in email
        return await super().add(
            id=id,
            name=name,
            email=email,
            password=password,
            is_admin=is_admin,
        )

    async def signin(self, email: str, password: str) -> uuid.UUID:
        """Sign a user in and save the user info in the session store.

        Returns:
            uuid - id of the session object
        """
        if user := await self.filter(User.email == email):
            if user[0].password == password:
                session_id = uuid.uuid4()
                SESSION[str(session_id)] = user[0]
                return session_id

        raise Exception("Invalid email or password")
