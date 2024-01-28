import httpx


async def test_part_one_root(client: httpx.AsyncClient):
    resp = await client.get("/part1/")
    assert "ExecutionResult(data={&#39;me&#39;: None}, errors=None)" in resp.text
    assert resp.status_code == 200, resp.text
