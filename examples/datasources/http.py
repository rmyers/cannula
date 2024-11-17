import dataclasses
import pathlib
import httpx
from cannula import CannulaAPI, Context, ResolveInfo
from cannula.datasource import http

from .database import DBUser, DBWidget, create_tables, drop_tables, session
from .api import remote_app

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
        return await info.context.widgets.get_widgets(self.id)


# Our HTTP datasources
class UserDatasource(
    http.HTTPDataSource[User],
    graph_model=User,
    base_url="http://localhost",
):

    async def get_user(self, user_id: int) -> User | None:
        response = await self.get(f"/users/{user_id}")
        return self.model_from_response(response)


class WidgetDatasource(
    http.HTTPDataSource[Widget],
    graph_model=Widget,
    base_url="http://localhost",
):

    async def get_widgets(self, user_id: int) -> list[Widget]:
        response = await self.get(f"/users/{user_id}/widgets")
        return self.model_list_from_response(response)


# Create a custom context and add the datasource
class MyContext(Context):
    def __init__(self, client: httpx.AsyncClient) -> None:
        self.users = UserDatasource(client=client)
        self.widgets = WidgetDatasource(client=client)


# Example query that uses the UserRepository on the context object
async def get_user(info: ResolveInfo[MyContext], id: int) -> User | None:
    return await info.context.users.get_user(id)


# Our example graph api
api = CannulaAPI(ROOT / "schema.graphql", root_value={"user": get_user})


async def main():
    await create_tables()
    # Create some data
    async with session() as db_session:
        user = DBUser(id=1, name="ted", email="ted@lasso.com", password="pass")
        widget1 = DBWidget(id=1, name="Hammer", user_id=1, type="tool")
        widget2 = DBWidget(id=2, name="Drill", user_id=1, type="tool")
        widget3 = DBWidget(id=3, name="Nail", user_id=1, type="tool")
        db_session.add_all([user, widget1, widget2, widget3])
        await db_session.commit()

    # Create a httpx client that responds with the 'remote_app' and add to context
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=remote_app)
    ) as client:

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
            context=MyContext(client),
        )

    await drop_tables()

    return results


if __name__ == "__main__":
    import asyncio

    print(asyncio.run(main()))
