from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from httpx import AsyncClient
import os
from contextlib import asynccontextmanager

USERS_BASE_URL = os.getenv("USERS_BASE_URL", "http://users:8080")
ORDERS_BASE_URL = os.getenv("ORDERS_BASE_URL", "http://orders:8080")
PAYMENTS_BASE_URL = os.getenv("PAYMENTS_BASE_URL", "http://payments:8080")

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http = AsyncClient(timeout=15)
    yield
    await app.state.http.aclose()

app = FastAPI(lifespan=lifespan)

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

async def _forward(req: Request, base: str, suffix: str):
    url = f"{base}{suffix}"
    method = req.method.upper()
    headers = {k: v for k, v in req.headers.items() if k.lower() != "host"}
    body = await req.body()
    
    r = await app.state.http.request(
        method,
        url,
        headers=headers,
        content=body,
        params=req.query_params
    )
    
    try:
        data = r.json() if r.content else None
        return JSONResponse(status_code=r.status_code, content=data)
    except Exception:
        return JSONResponse(status_code=r.status_code, content=r.text)

# Users
@app.api_route("/users/", methods=["GET", "POST"])
async def users_root(req: Request):
    return await _forward(req, USERS_BASE_URL, "/users/")

@app.api_route("/users/{uid}", methods=["GET", "PUT", "DELETE"])
async def users_by_id(uid: int, req: Request):
    return await _forward(req, USERS_BASE_URL, f"/users/{uid}")

# Orders
@app.api_route("/orders/", methods=["GET", "POST"])
async def orders_root(req: Request):
    return await _forward(req, ORDERS_BASE_URL, "/orders/")

@app.api_route("/orders/{oid}", methods=["GET", "PUT", "DELETE"])
async def orders_by_id(oid: int, req: Request):
    return await _forward(req, ORDERS_BASE_URL, f"/orders/{oid}")

# Payments
@app.api_route("/payments/", methods=["GET", "POST"])
async def payments_root(req: Request):
    return await _forward(req, PAYMENTS_BASE_URL, "/payments/")

@app.api_route("/payments/{pid}", methods=["GET", "PUT", "DELETE"])
async def payments_by_id(pid: int, req: Request):
    return await _forward(req, PAYMENTS_BASE_URL, f"/payments/{pid}")

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
