import dataclasses
import pathlib
import logging

from cannula import ResolveInfo, Context, CannulaAPI
from cannula.datasource.orm import DatabaseRepository
from sqlalchemy.ext.asyncio import async_sessionmaker

from .database import DBUser, DBWidget, create_tables, drop_tables, session

ROOT = pathlib.Path(__file__).parent


# Graph Models that our repositories use to return data
@dataclasses.dataclass
class Widget:
    id: int
    user_id: int
    name: str


@dataclasses.dataclass
class User:
    id: int
    email: str | None
    name: str | None

    # This resolver uses the widgets repository that is on the context
    async def widgets(self, info: ResolveInfo["MyContext"]) -> list["Widget"]:
        return await info.context.widgets.get_for_user(self.id)


# Repositories for CRUD operations on our database
class UserRepository(
    DatabaseRepository[DBUser, User],
    db_model=DBUser,
    graph_model=User,
):

    async def get_user(self, pk: int) -> User | None:
        return await self.get_model(pk)


class WidgetRepository(
    DatabaseRepository[DBWidget, Widget],
    db_model=DBWidget,
    graph_model=Widget,
):

    async def get_for_user(self, user_id: int) -> list[Widget]:
        return await self.get_models(DBWidget.user_id == user_id)


# ResolveInfo Context that is passed to all resolvers.
class MyContext(Context):
    def __init__(self, session_maker: async_sessionmaker) -> None:
        self.widgets = WidgetRepository(session_maker)
        self.users = UserRepository(session_maker)


# Example query that uses the UserRepository on the context object
async def get_user(info: ResolveInfo[MyContext], id: int) -> User | None:
    return await info.context.users.get_user(id)


# Our example graph api
api = CannulaAPI(ROOT / "schema.graphql", root_value={"user": get_user})


async def main():
    await create_tables()

    # Create some data
    context = MyContext(session)
    await context.users.add(id=1, name="ted", email="ted@lasso.com", password="pass")
    await context.widgets.add(id=1, name="Hammer", user_id=1, type="tool")
    await context.widgets.add(id=2, name="Drill", user_id=1, type="tool")
    await context.widgets.add(id=3, name="Nail", user_id=1, type="tool")

    # Run a query and return nested data
    results = await api.call(
        """
        query User {
            user(id: 1) {
                widgets {
                    name
                }
            }
            another: user(id: 1) {
                widgets {
                    name
                }
            }
        }
        """,
        context=context,
    )

    await drop_tables()
    return results


if __name__ == "__main__":
    import asyncio

    print(asyncio.run(main()))
