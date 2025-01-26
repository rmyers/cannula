import httpx

from dashboard.part3.seed_part3 import seed_data

QUERY = """
    query People {
        people {
            name
            email
            id
        }
    }
    """


async def test_part_three_graph(test_config, client: httpx.AsyncClient):
    user_ids = await seed_data(test_config.session)
    resp = await client.post("/part3/graph", json={"query": QUERY})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data.get("errors") is None
    assert data.get("data") == {
        "people": [
            {"email": "sam@ex.com", "name": "test", "id": f"{user_ids[0]}"},
            {"email": "sammie@ex.com", "name": "another", "id": f"{user_ids[1]}"},
        ],
    }
