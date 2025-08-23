import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_health():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}

@pytest.mark.asyncio
async def test_crud_payment():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Create
        resp = await ac.post("/payments/", json={"order_id": 1, "amount": 50.0})
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "pending"
        pid = data["id"]

        # Read
        resp = await ac.get(f"/payments/{pid}")
        assert resp.status_code == 200
        assert resp.json()["order_id"] == 1

        # Update
        resp = await ac.put(f"/payments/{pid}", json={"order_id": 1, "amount": 75.0, "status": "pending"})
        assert resp.status_code == 200
        assert resp.json()["amount"] == 75.0

        # Process
        resp = await ac.post(f"/payments/{pid}/process")
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"

        # Refund
        resp = await ac.post(f"/payments/{pid}/refund")
        assert resp.status_code == 200
        assert resp.json()["status"] == "refunded"

        # Filter by status
        resp = await ac.get("/payments/?status=refunded")
        assert resp.status_code == 200
        assert any(p["status"] == "refunded" for p in resp.json())

        # Delete
        resp = await ac.delete(f"/payments/{pid}")
        assert resp.status_code == 204

        # Not found after delete
        resp = await ac.get(f"/payments/{pid}")
        assert resp.status_code == 404
