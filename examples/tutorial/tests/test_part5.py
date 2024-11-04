import httpx
import uuid

from dashboard.core.repository import QuotaRepository, UserRepository

QUERY = """
    query People {
        people {
            name
            email
            quota {
                resource
                limit
            }
            overQuota(resource: "water") {
                count
            }
        }
    }
    """


async def test_part_five_graph(client: httpx.AsyncClient, session):
    user_id = uuid.uuid4()
    admin_id = uuid.uuid4()
    users = UserRepository(session=session)
    quotas = QuotaRepository(session=session)
    await users.add(id=user_id, name="test", email="sam@example.com", password="test")
    await users.add(
        id=admin_id, name="adder", email="admin@example.com", password="test"
    )
    await quotas.add(user_id=user_id, resource="fire", limit=10, count=4)
    await quotas.add(user_id=user_id, resource="water", limit=15, count=4)
    await quotas.add(user_id=admin_id, resource="fire", limit=5, count=4)

    resp = await client.post("/part5/graph", json={"query": QUERY})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data.get("errors") is None
    assert data.get("data") == {
        "people": [
            {
                "email": "sam@example.com",
                "name": "test",
                "overQuota": {"count": 4},
                "quota": [
                    {"limit": 10, "resource": "fire"},
                    {"limit": 15, "resource": "water"},
                ],
            },
            {
                "email": "admin@example.com",
                "name": "adder",
                "overQuota": None,
                "quota": [{"limit": 5, "resource": "fire"}],
            },
        ],
    }
