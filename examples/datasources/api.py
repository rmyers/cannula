from typing import AsyncGenerator, Annotated
from fastapi import FastAPI, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .database import DBWidget, DBUser, session

remote_app = FastAPI()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with session() as db_session:
        yield db_session


class Widget(BaseModel):
    id: int
    user_id: int
    name: str


class User(BaseModel):
    id: int
    email: str | None
    name: str | None


@remote_app.get("/users/{user_id}")
async def get_user(
    user_id: int, db_session: Annotated[AsyncSession, Depends(get_session)]
):
    if user := await db_session.get(DBUser, user_id):
        return User(**user.__dict__)


@remote_app.get("/users/{user_id}/widgets")
async def get_user_widgets(
    user_id: int, db_session: Annotated[AsyncSession, Depends(get_session)]
):
    query = select(DBWidget).where(DBWidget.user_id == user_id)
    widgets = await db_session.scalars(query)
    return [Widget(**w.__dict__) for w in widgets]
