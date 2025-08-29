from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from sqlalchemy import Column, Integer, String, Float, create_engine, MetaData
from sqlalchemy.orm import declarative_base
import databases
from pathlib import Path
from contextlib import asynccontextmanager

# Ensure ./data directory exists
Path("./data").mkdir(parents=True, exist_ok=True)

# Database setup
DATABASE_URL = "sqlite:///./data/payments.db"
database = databases.Database(DATABASE_URL)
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
Base = declarative_base()
metadata = MetaData()

class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, index=True)
    amount = Column(Float)
    status = Column(String, default="pending")

Base.metadata.create_all(bind=engine)

# Pydantic models
class PaymentCreate(BaseModel):
    order_id: int
    amount: float = Field(..., ge=0, description="Amount must be non-negative")

class PaymentUpdate(BaseModel):
    order_id: int
    amount: float = Field(..., ge=0)
    status: str

class PaymentResponse(PaymentCreate):
    id: int
    status: str

    model_config = ConfigDict(from_attributes=True)

# Lifespan for db connect/disconnect
@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.connect()
    yield
    await database.disconnect()

app = FastAPI(lifespan=lifespan)

# Routes
@app.post("/payments/", response_model=PaymentResponse, status_code=201)
async def create_payment(payment: PaymentCreate):
    query = Payment.__table__.insert().values(**payment.model_dump())
    payment_id = await database.execute(query)
    return PaymentResponse(id=int(payment_id), status="pending", **payment.model_dump())

@app.get("/payments/", response_model=List[PaymentResponse])
async def list_payments(status: Optional[str] = Query(None, description="Filter by status")):
    query = Payment.__table__.select()
    if status:
        query = query.where(Payment.status == status)
    rows = await database.fetch_all(query)
    return [
        PaymentResponse(
            id=r["id"], order_id=r["order_id"], amount=r["amount"], status=r["status"] or "pending"
        )
        for r in rows
    ]

@app.get("/payments/{payment_id}", response_model=PaymentResponse)
async def get_payment(payment_id: int):
    row = await database.fetch_one(Payment.__table__.select().where(Payment.id == payment_id))
    if not row:
        raise HTTPException(status_code=404, detail="Payment not found")
    return PaymentResponse(
        id=row["id"], order_id=row["order_id"], amount=row["amount"], status=row["status"] or "pending"
    )

@app.put("/payments/{payment_id}", response_model=PaymentResponse)
async def update_payment(payment_id: int, payload: PaymentUpdate):
    existing = await database.fetch_one(Payment.__table__.select().where(Payment.id == payment_id))
    if not existing:
        raise HTTPException(status_code=404, detail="Payment not found")
    await database.execute(Payment.__table__.update().where(Payment.id == payment_id).values(**payload.model_dump()))
    return PaymentResponse(id=payment_id, **payload.model_dump())

@app.delete("/payments/{payment_id}", status_code=204)
async def delete_payment(payment_id: int):
    existing = await database.fetch_one(Payment.__table__.select().where(Payment.id == payment_id))
    if not existing:
        raise HTTPException(status_code=404, detail="Payment not found")
    await database.execute(Payment.__table__.delete().where(Payment.id == payment_id))
    return

@app.post("/payments/{payment_id}/process", response_model=PaymentResponse)
async def process_payment(payment_id: int):
    payment = await database.fetch_one(Payment.__table__.select().where(Payment.id == payment_id))
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    new_status = "completed" if payment["amount"] > 0 else "failed"
    await database.execute(Payment.__table__.update().where(Payment.id == payment_id).values(status=new_status))
    return PaymentResponse(id=payment_id, order_id=payment["order_id"], amount=payment["amount"], status=new_status)

@app.post("/payments/{payment_id}/refund", response_model=PaymentResponse)
async def refund_payment(payment_id: int):
    payment = await database.fetch_one(Payment.__table__.select().where(Payment.id == payment_id))
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    if payment["status"] != "completed":
        raise HTTPException(status_code=400, detail="Only completed payments can be refunded")
    await database.execute(Payment.__table__.update().where(Payment.id == payment_id).values(status="refunded"))
    return PaymentResponse(id=payment_id, order_id=payment["order_id"], amount=payment["amount"], status="refunded")

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

from prometheus_fastapi_instrumentator import Instrumentator

instrumentator = Instrumentator()
instrumentator.instrument(app).expose(app)  # Exposes /metrics
