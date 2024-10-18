import httpx
import uuid

from dashboard.core.repository import UserRepository

QUERY = """
    query People {
        people {
            name
            ... on User {
                email
                quota {
                    limit
                }
            }
            ... on Admin {
                email
            }
        }
    }
    """


async def test_part_three_graph(client: httpx.AsyncClient, session):
    user_id = uuid.uuid4()
    admin_id = uuid.uuid4()
    users = UserRepository(session=session)
    await users.add(id=user_id, name="test", email="sam@example.com", password="test")
    await users.add(
        id=admin_id, name="adder", email="admin@example.com", password="test"
    )

    resp = await client.post("/part3/graph", json={"query": QUERY})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data.get("errors") is None
    assert data.get("data") == {
        "people": [
            {"email": "sam@example.com", "name": "test", "quota": None},
            {"email": "admin@example.com", "name": "adder"},
        ],
    }
