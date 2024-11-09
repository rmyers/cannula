import httpx
import uuid

from dashboard.core.config import config
from dashboard.part5.repository import QuotaRepository, UserRepository

QUERY = """
    query People($id: UUID!) {
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
        person(id: $id) {
            name
            email
        }
        another: person(id: $id) {
            name
            email
        }
    }
    """


async def test_part_five_graph(client: httpx.AsyncClient, mocker):
    user_id = uuid.uuid4()
    admin_id = uuid.uuid4()
    users = UserRepository(config.session)
    quotas = QuotaRepository(config.session)
    user_from_db = mocker.spy(users, "from_db")
    quotas_from_db = mocker.spy(quotas, "from_db")
    await users.add(id=user_id, name="test", email="sam@example.com", password="test")
    await users.add(
        id=admin_id, name="adder", email="admin@example.com", password="test"
    )
    await quotas.add(user_id=user_id, resource="fire", limit=10, count=4)
    await quotas.add(user_id=user_id, resource="water", limit=15, count=4)
    await quotas.add(user_id=admin_id, resource="fire", limit=5, count=4)

    resp = await client.post(
        "/part5/graph",
        json={
            "query": QUERY,
            "variables": {"id": str(user_id)},
        },
    )
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
        "person": {"email": "sam@example.com", "name": "test"},
        "another": {"email": "sam@example.com", "name": "test"},
    }

    # Make sure we only called the database the correct amount
    assert user_from_db.call_count == 2
    assert quotas_from_db.call_count == 3
