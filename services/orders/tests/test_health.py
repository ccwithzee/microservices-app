import pytest
import sys, os
from httpx import AsyncClient

# Ensure "app" is on sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.main import app

@pytest.mark.asyncio
async def test_health():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        res = await ac.get("/healthz")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}

@pytest.mark.asyncio
async def test_crud_order():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # 1. Create
        payload = {"user_id": 1, "item_name": "Book", "quantity": 2}
        res = await ac.post("/orders/", json=payload)
        assert res.status_code == 201
        order = res.json()
        order_id = order["id"]
        assert order["item_name"] == "Book"

        # 2. List
        res = await ac.get("/orders/")
        assert res.status_code == 200
        assert any(o["id"] == order_id for o in res.json())

        # 3. Get by ID
        res = await ac.get(f"/orders/{order_id}")
        assert res.status_code == 200
        assert res.json()["id"] == order_id

        # 4. Update
        updated = {"user_id": 1, "item_name": "Laptop", "quantity": 1}
        res = await ac.put(f"/orders/{order_id}", json=updated)
        assert res.status_code == 200
        assert res.json()["item_name"] == "Laptop"

        # 5. Delete
        res = await ac.delete(f"/orders/{order_id}")
        assert res.status_code == 204

        # 6. Verify deletion
        res = await ac.get(f"/orders/{order_id}")
        assert res.status_code == 404
