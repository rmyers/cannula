#!./venv/bin/python

import asyncio
import time
import typing

import ariadne
import ariadne.asgi
import cannula
import httpx
import fastapi
import pydantic


class Widget(pydantic.BaseModel):
    name: str
    use: str
    quantity: int


WIDGETS: typing.List[dict] = [
    {"name": "screw driver", "use": "tighten", "quantity": 10},
    {"name": "hammer", "use": "nail", "quantity": 15},
    {"name": "saw", "use": "cut", "quantity": 6},
    {"name": "wrench", "use": "tighten", "quantity": 20},
    {"name": "bolt", "use": "fasten", "quantity": 13},
]

schema = """
type Widget {
    name: String
    use: String
    quantity: Int
}

type Query {
    get_widgets(use: String): [Widget]
}
"""

document = """
    query widgets ($use: String) {
        get_widgets(use: $use) {
            name
            use
            quantity
        }
    }
"""


query = ariadne.QueryType()
api = fastapi.FastAPI()


def _get_widgets(use: str) -> typing.List[dict]:
    matches = []
    for widget in WIDGETS:
        if widget.get("use") == use:
            matches.append(widget)

    return matches


@api.get("/api/fastapi", response_model=typing.List[Widget])
async def get_widgets_with_fastapi(use: str) -> typing.Any:
    return _get_widgets(use)


@query.field("get_widgets")
def resolve_get_widgets(_, _info, use: str) -> typing.List[dict]:
    return _get_widgets(use)


# Create executable schema instance
exe_schema = ariadne.make_executable_schema(schema, query)
ariadne_app = ariadne.asgi.GraphQL(exe_schema)
cannula_app = cannula.API(__name__, schema=[schema])


@cannula_app.resolver("Query")
def get_widgets(_, _info, use: str) -> typing.Any:
    return _get_widgets(use)


@api.post("/api/ariadne")
async def get_ariadne_app(request: fastapi.Request) -> typing.Any:
    return await ariadne_app.handle_request(request)


@api.get("/api/cannula")
async def get_cannula_app(request: fastapi.Request) -> typing.Any:
    results = await cannula_app.call(
        cannula.gql(document), request, variables={"use": "tighten"}
    )
    return {"data": results.data, "errors": results.errors}


async def test_performance():
    client = httpx.AsyncClient(app=api, base_url="http://localhost")

    start = time.perf_counter()
    for x in range(1000):
        resp = await client.get("/api/fastapi?use=tighten")
        assert resp.status_code == 200
    stop = time.perf_counter()
    fast_results = stop - start

    print("\nperformance test results:")
    print(f"fastapi: {fast_results}")

    start = time.perf_counter()
    for _x in range(1000):
        resp = await client.post(
            "/api/ariadne",
            json={"query": document, "variables": {"use": "tighten"}},
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 200

    stop = time.perf_counter()
    ariadne_results = stop - start

    print(f"ariadne results: {ariadne_results}")

    start = time.perf_counter()
    for _x in range(1000):
        resp = await client.get(
            "/api/cannula",
        )
        assert resp.status_code == 200

    stop = time.perf_counter()
    cannula_results = stop - start

    print(f"cannula results: {cannula_results}")
