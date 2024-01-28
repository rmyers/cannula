import httpx


async def test_part_one_root(client: httpx.AsyncClient):
    resp = await client.get("/part2/")
    assert (
        "ExecutionResult(data={&#39;me&#39;: {&#39;id&#39;: &#39;1&#39;, &#39;name&#39;: &#39;Tiny Tim&#39;}}, errors=None)"
        in resp.text
    )
    assert resp.status_code == 200, resp.text
