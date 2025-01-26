import httpx
import uuid

from dashboard.core.config import Config
from dashboard.part5.seed_part5 import seed_data
from dashboard.part5.gql.context import UserDatasource

QUERY = """
    query People {
        people {
            name
            email
            quota {
                resource
                limit
                user {
                    name
                }
            }
            overQuota(resource: "water") {
                count
            }
        }
    }
    """


async def test_part_four_graph(client: httpx.AsyncClient, test_config: Config):
    await seed_data(test_config.session)

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
                    {"limit": 10, "resource": "fire", "user": {"name": "test"}},
                    {"limit": 15, "resource": "water", "user": {"name": "test"}},
                ],
            },
            {
                "email": "admin@example.com",
                "name": "adder",
                "overQuota": None,
                "quota": [{"limit": 5, "resource": "fire", "user": {"name": "adder"}}],
            },
        ],
    }


MULTI_QUERY = """
    query People($id: UUID!) {
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


async def test_datasources_cache_identical_queries(
    client: httpx.AsyncClient, mocker, test_config: Config
):
    user_id = uuid.uuid4()
    await UserDatasource(test_config.session).add(
        id=user_id, name="frank", email="no@uc.com"
    )
    user_from_db = mocker.spy(UserDatasource, "from_db")
    resp = await client.post(
        "/part5/graph",
        json={
            "query": MULTI_QUERY,
            "variables": {"id": str(user_id)},
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data.get("errors") is None
    assert data.get("data") == {
        "person": {"email": "no@uc.com", "name": "frank"},
        "another": {"email": "no@uc.com", "name": "frank"},
    }

    # Make sure we only called the database the correct amount
    assert user_from_db.call_count == 2
