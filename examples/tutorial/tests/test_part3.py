import httpx

from dashboard.part3.models import add_data

QUERY = """
    query People($id: UUID!) {
        people {
            name
            email
            quota {
                limit
                user {
                    name
                }
            }
        }
        user(id: $id) {
            id
            name
        }
    }
    """


async def test_part_three_graph(client: httpx.AsyncClient):
    user_id = await add_data()
    resp = await client.post(
        "/part3/graph", json={"query": QUERY, "variables": {"id": user_id.hex}}
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data.get("errors") is None
    assert data.get("data") == {
        "people": [
            {
                "email": "sam@ex.com",
                "name": "test",
                "quota": [{"limit": 100, "user": {"name": "test"}}],
            },
        ],
        "user": {"id": str(user_id), "name": "test"},
    }
