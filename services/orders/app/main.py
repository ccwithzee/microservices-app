from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict
from typing import List
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import declarative_base
import databases
import os
from contextlib import asynccontextmanager

# Ensure data directory exists
os.makedirs("./data", exist_ok=True)

DATABASE_URL = "sqlite:///./data/orders.db"
database = databases.Database(DATABASE_URL)
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
Base = declarative_base()

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    item_name = Column(String, index=True)
    quantity = Column(Integer)

Base.metadata.create_all(bind=engine)

class OrderCreate(BaseModel):
    user_id: int
    item_name: str
    quantity: int

class OrderUpdate(BaseModel):
    user_id: int
    item_name: str
    quantity: int

class OrderResponse(OrderCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)  # ✅ replaces orm_mode

# ✅ use new lifespan instead of deprecated @on_event
@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.connect()
    yield
    await database.disconnect()

app = FastAPI(lifespan=lifespan)

@app.post("/orders/", response_model=OrderResponse, status_code=201)
async def create_order(order: OrderCreate):
    query = Order.__table__.insert().values(**order.dict())
    order_id = await database.execute(query)
    return {**order.dict(), "id": int(order_id)}

@app.get("/orders/", response_model=List[OrderResponse])
async def list_orders():
    rows = await database.fetch_all(Order.__table__.select())
    return [dict(r) for r in rows]

@app.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(order_id: int):
    order = await database.fetch_one(Order.__table__.select().where(Order.id == order_id))
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return dict(order)

@app.put("/orders/{order_id}", response_model=OrderResponse)
async def update_order(order_id: int, payload: OrderUpdate):
    existing = await database.fetch_one(Order.__table__.select().where(Order.id == order_id))
    if not existing:
        raise HTTPException(status_code=404, detail="Order not found")
    await database.execute(Order.__table__.update().where(Order.id == order_id).values(**payload.dict()))
    return {"id": order_id, **payload.dict()}

@app.delete("/orders/{order_id}", status_code=204)
async def delete_order(order_id: int):
    existing = await database.fetch_one(Order.__table__.select().where(Order.id == order_id))
    if not existing:
        raise HTTPException(status_code=404, detail="Order not found")
    await database.execute(Order.__table__.delete().where(Order.id == order_id))
    return

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


# -----------------------------
# Prometheus Metrics
# -----------------------------
from prometheus_fastapi_instrumentator import Instrumentator

instrumentator = Instrumentator()
instrumentator.instrument(app).expose(app)  # Exposes /metrics