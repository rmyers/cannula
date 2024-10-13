import httpx

import cannula

QUERY = """
    query LoggedInUser {
        me {
            id
            name
        }
    }
    """


async def test_part_three_graph(client: httpx.AsyncClient):
    resp = await client.post("/part3/graph", json={"query": QUERY})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data.get("data") == {"me": {"id": "1", "name": "Tiny Tim"}}
