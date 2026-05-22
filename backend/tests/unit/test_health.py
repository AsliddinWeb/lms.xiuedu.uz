from httpx import AsyncClient


async def test_root(client: AsyncClient) -> None:
    response = await client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["app"] == "XIU LMS Backend"
    assert body["version"] == "0.1.0"


async def test_health(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["app"] == "XIU LMS Backend"
