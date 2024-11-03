#!./venv/bin/python

import asyncio
import time
import typing

import ariadne
import ariadne.asgi
import cannula
import cannula.contrib.asgi
import httpx
import fastapi
import pydantic

NUM_RUNS = 1000


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

invalid_document = """
    query blah ( { }
"""

invalid_query = """
    query widgets ($use: String) {
        get_nonexistent(use: $use) {
            foo
        }
    }
"""


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


async def resolve_get_widgets(info, use: str) -> typing.List[dict]:
    return _get_widgets(use)


# Create executable schema instance
exe_schema = ariadne.make_executable_schema(schema)

# Use the root value for our simple resolver. This way both
# Ariadne and Cannula use the same logic to resolve a query
ariadne_app = ariadne.asgi.GraphQL(
    exe_schema, root_value={"get_widgets": resolve_get_widgets}
)
cannula_app = cannula.CannulaAPI(
    schema=schema, root_value={"get_widgets": resolve_get_widgets}
)


@api.post("/api/ariadne")
async def get_ariadne_app(request: fastapi.Request) -> typing.Any:
    return await ariadne_app.handle_request(request)


@api.post("/api/cannula")
async def get_cannula_app(
    request: fastapi.Request, payload: cannula.contrib.asgi.GraphQLPayload
) -> typing.Any:
    results = await cannula_app.call(
        payload.query, request, variables=payload.variables
    )
    errors = [e.formatted for e in results.errors] if results.errors else None
    return {"data": results.data, "errors": errors}


async def test_performance():
    client = httpx.AsyncClient(app=api, base_url="http://localhost")

    start = time.perf_counter()
    for x in range(NUM_RUNS):
        resp = await client.get("/api/fastapi?use=tighten")
        assert resp.status_code == 200, resp.text
        assert resp.json() == [
            {"name": "screw driver", "quantity": 10, "use": "tighten"},
            {"name": "wrench", "quantity": 20, "use": "tighten"},
        ]

    stop = time.perf_counter()
    fast_results = stop - start

    print("\nperformance test results:")
    print(f"fastapi: {fast_results}")

    start = time.perf_counter()
    for _x in range(NUM_RUNS):
        resp = await client.post(
            "/api/ariadne",
            json={"query": document, "variables": {"use": "tighten"}},
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["get_widgets"] == [
            {"name": "screw driver", "quantity": 10, "use": "tighten"},
            {"name": "wrench", "quantity": 20, "use": "tighten"},
        ]

    stop = time.perf_counter()
    ariadne_results = stop - start

    print(f"ariadne results: {ariadne_results}")

    start = time.perf_counter()
    for _x in range(NUM_RUNS):
        resp = await client.post(
            "/api/cannula",
            json={"query": document, "variables": {"use": "tighten"}},
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["get_widgets"] == [
            {"name": "screw driver", "quantity": 10, "use": "tighten"},
            {"name": "wrench", "quantity": 20, "use": "tighten"},
        ]

    stop = time.perf_counter()
    cannula_results = stop - start

    print(f"cannula results: {cannula_results}")


async def test_performance_invalid_request():
    client = httpx.AsyncClient(app=api, base_url="http://localhost")

    start = time.perf_counter()
    for x in range(NUM_RUNS):
        resp = await client.get("/api/fastapi")
        assert resp.status_code == 422, resp.text

    stop = time.perf_counter()
    fast_results = stop - start

    print("\nperformance test results:")
    print(f"fastapi: {fast_results}")

    start = time.perf_counter()
    for _x in range(NUM_RUNS):
        resp = await client.post(
            "/api/ariadne",
            json={"query": invalid_document, "variables": {"use": "tighten"}},
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 400, resp.text
        errors = resp.json()["errors"]
        assert len(errors) == 1
        assert errors[0]["message"] == "Syntax Error: Expected '$', found '{'."

    stop = time.perf_counter()
    ariadne_results = stop - start

    print(f"ariadne results: {ariadne_results}")

    start = time.perf_counter()
    for _x in range(NUM_RUNS):
        resp = await client.post(
            "/api/cannula",
            json={"query": invalid_document, "variables": {"use": "tighten"}},
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 200, resp.text
        errors = resp.json()["errors"]
        assert len(errors) == 1
        assert errors[0]["message"] == "Syntax Error: Expected '$', found '{'."

    stop = time.perf_counter()
    cannula_results = stop - start

    print(f"cannula results: {cannula_results}")


async def test_performance_invalid_query():
    client = httpx.AsyncClient(app=api, base_url="http://localhost")

    start = time.perf_counter()
    for x in range(NUM_RUNS):
        resp = await client.get("/api/fastapi")
        assert resp.status_code == 422, resp.text

    stop = time.perf_counter()
    fast_results = stop - start

    print("\nperformance test results:")
    print(f"fastapi: {fast_results}")

    start = time.perf_counter()
    for _x in range(NUM_RUNS):
        resp = await client.post(
            "/api/ariadne",
            json={"query": invalid_query, "variables": {"use": "tighten"}},
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 400, resp.text
        errors = resp.json()["errors"]
        assert len(errors) == 1
        assert (
            errors[0]["message"]
            == "Cannot query field 'get_nonexistent' on type 'Query'."
        )

    stop = time.perf_counter()
    ariadne_results = stop - start

    print(f"ariadne results: {ariadne_results}")

    start = time.perf_counter()
    for _x in range(NUM_RUNS):
        resp = await client.post(
            "/api/cannula",
            json={"query": invalid_query, "variables": {"use": "tighten"}},
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 200, resp.text
        errors = resp.json()["errors"]
        assert len(errors) == 1
        assert (
            errors[0]["message"]
            == "Cannot query field 'get_nonexistent' on type 'Query'."
        )

    stop = time.perf_counter()
    cannula_results = stop - start

    print(f"cannula results: {cannula_results}")
