import os

import httpx
import pytest


@pytest.fixture()
async def client(tmp_path, monkeypatch):
    db_path = tmp_path / "traderai_test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("SECRET_KEY", "test-secret")

    from main import app

    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as test_client:
            yield test_client


@pytest.mark.asyncio
async def test_health_smoke(client):
    response = await client.get("/api/v1/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert payload["database"] == "healthy"
    assert payload["version"]


@pytest.mark.asyncio
async def test_mt5_status_smoke(client):
    response = await client.get("/api/v1/mt5/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert "connected" in payload["data"]


@pytest.mark.asyncio
async def test_static_pages_smoke(client):
    for path in ["/", "/login.html", "/dashboard.html", "/terminal.html"]:
        response = await client.get(path)
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
