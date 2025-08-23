import pytest
import respx
import httpx
from httpx import AsyncClient
from asgi_lifespan import LifespanManager
from app.main import app  # your FastAPI gateway app

USERS_BASE = "http://users:8080"
ORDERS_BASE = "http://orders:8080"
PAYMENTS_BASE = "http://payments:8080"


@pytest.mark.asyncio
async def test_healthz():
    async with LifespanManager(app):  # ensures startup events run
        async with AsyncClient(app=app, base_url="http://test") as ac:
            res = await ac.get("/healthz")
        assert res.status_code == 200
        assert res.json() == {"status": "ok"}


@pytest.mark.asyncio
@respx.mock
async def test_gateway_forwards_to_users():
    # Patch http client in app.state
    async with LifespanManager(app):
        app.state.http = httpx.AsyncClient()

        # Mock downstream GET /users/1
        respx.get(f"{USERS_BASE}/users/1").mock(
            return_value=httpx.Response(200, json={"id": 1, "username": "alice"})
        )

        async with AsyncClient(app=app, base_url="http://test") as ac:
            res = await ac.get("/users/1")
        assert res.status_code == 200
        assert res.json() == {"id": 1, "username": "alice"}


@pytest.mark.asyncio
@respx.mock
async def test_gateway_propagates_404_from_orders():
    async with LifespanManager(app):
        app.state.http = httpx.AsyncClient()

        # Mock downstream 404
        respx.get(f"{ORDERS_BASE}/orders/999").mock(
            return_value=httpx.Response(404, json={"detail": "Not found"})
        )

        async with AsyncClient(app=app, base_url="http://test") as ac:
            res = await ac.get("/orders/999")
        assert res.status_code == 404
        assert res.json() == {"detail": "Not found"}


@pytest.mark.asyncio
@respx.mock
async def test_gateway_forwards_post_to_payments():
    async with LifespanManager(app):
        app.state.http = httpx.AsyncClient()

        # Mock downstream POST /payments/
        respx.post(f"{PAYMENTS_BASE}/payments/").mock(
            return_value=httpx.Response(201, json={"payment_id": 42, "status": "success"})
        )

        async with AsyncClient(app=app, base_url="http://test") as ac:
            res = await ac.post("/payments/", json={"amount": 500})
        assert res.status_code == 201
        assert res.json() == {"payment_id": 42, "status": "success"}


@pytest.mark.asyncio
@respx.mock
async def test_gateway_passes_query_params():
    async with LifespanManager(app):
        app.state.http = httpx.AsyncClient()

        # Verify querystring is forwarded as-is
        route = respx.get(f"{USERS_BASE}/users/").mock(
            return_value=httpx.Response(200, json=[{"id": 1}, {"id": 2}])
        )

        async with AsyncClient(app=app, base_url="http://test") as ac:
            res = await ac.get("/users/?limit=2")
        assert res.status_code == 200
        assert res.json() == [{"id": 1}, {"id": 2}]
        assert route.called
        # Last downstream request URL should include the querystring
        assert str(route.calls.last.request.url).endswith("/users/?limit=2")
