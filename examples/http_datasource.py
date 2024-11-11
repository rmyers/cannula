import logging
import typing
from dataclasses import dataclass

import cannula
import fastapi
import httpx
from cannula.context import Context, ResolveInfo
from cannula.datasource import http


logging.basicConfig(level=logging.DEBUG)

# For demo purposes we'll just use a local asgi application
remote_app = fastapi.FastAPI()


@remote_app.get("/widgets")
async def get_widgets():
    return [{"name": "hammer", "type": "tool"}]


SCHEMA = cannula.gql(
    """
    type Widget {
        name: String
        type: String
    }

    type Query {
        widgets: [Widget]
    }

"""
)


@dataclass
class Widget:
    name: str
    type: str


# Our actual datasource object
class WidgetDatasource(
    http.HTTPDataSource[Widget], graph_model=Widget, base_url="http://localhost"
):

    async def get_widgets(self) -> list[Widget]:
        response = await self.get("/widgets")
        return self.model_list_from_response(response)


# Create a custom context and add the datasource
class CustomContext(Context):

    def __init__(self, client) -> None:
        self.widget_datasource = WidgetDatasource(client=client)


async def list_widgets(info: ResolveInfo[CustomContext]):
    return await info.context.widget_datasource.get_widgets()


api = cannula.CannulaAPI(
    schema=SCHEMA,
    root_value={"widgets": list_widgets},
)


async def main():
    # This does the same query twice to show the results are cached
    query = cannula.gql(
        """
        query Widgets {
            widgets: widgets {
                name
                type
            }
            another: widgets {
                name
                type
            }
        }
    """
    )

    # Create a httpx client that responds with the 'remote_app' and add to context
    client = httpx.AsyncClient(transport=httpx.ASGITransport(app=remote_app))

    results = await api.call(query, context=CustomContext(client))
    print(results.data, results.errors)
    return results.data


if __name__ == "__main__":
    import asyncio

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
