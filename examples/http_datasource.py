import logging
import typing

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


# Create a httpx client that responds with the 'remote_app'
client = httpx.AsyncClient(transport=httpx.ASGITransport(app=remote_app))


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


# Our actual datasource object
class WidgetDatasource(http.HTTPDataSource):
    # set our base url to work with the demo fastapi app
    base_url = "http://localhost"

    async def get_widgets(self):
        return await self.get("/widgets")


# Create a custom context and add the datasource
class CustomContext(Context):
    widget_datasource: WidgetDatasource

    def handle_request(self, request: typing.Any) -> typing.Any:
        # Initialize the datasource using the request and
        # set the client to use the demo client app
        self.widget_datasource = WidgetDatasource(request, client=client)
        return request


api = cannula.API(schema=SCHEMA, context=CustomContext)


@api.query("widgets")
async def list_widgets(parent, info: ResolveInfo[CustomContext]):
    return await info.context.widget_datasource.get_widgets()


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

    results = await api.call(query)
    print(results.data, results.errors)
    return results.data


if __name__ == "__main__":
    import asyncio

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
