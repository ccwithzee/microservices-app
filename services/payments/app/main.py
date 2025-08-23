from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from sqlalchemy import Column, Integer, String, Float, create_engine
from sqlalchemy.ext.declarative import declarative_base
import databases
import os

# Ensure data directory exists
os.makedirs("./data", exist_ok=True)

DATABASE_URL = "sqlite:///./data/payments.db"
database = databases.Database(DATABASE_URL)
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
Base = declarative_base()

class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, index=True)
    amount = Column(Float)
    status = Column(String, default="pending")

Base.metadata.create_all(bind=engine)

class PaymentCreate(BaseModel):
    order_id: int
    amount: float

class PaymentUpdate(BaseModel):
    order_id: int
    amount: float
    status: str

class PaymentResponse(PaymentCreate):
    id: int
    status: str
    class Config:
        from_attributes = True

app = FastAPI()

@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

@app.post("/payments/", response_model=PaymentResponse, status_code=201)
async def create_payment(payment: PaymentCreate):
    query = Payment.__table__.insert().values(**payment.dict())
    payment_id = await database.execute(query)
    return PaymentResponse(id=int(payment_id), status="pending", **payment.dict())

@app.get("/payments/", response_model=List[PaymentResponse])
async def list_payments():
    rows = await database.fetch_all(Payment.__table__.select())
    return [
        PaymentResponse(
            id=r["id"],
            order_id=r["order_id"],
            amount=r["amount"],
            status=r["status"] or "pending"
        ) for r in rows
    ]

@app.get("/payments/{payment_id}", response_model=PaymentResponse)
async def get_payment(payment_id: int):
    row = await database.fetch_one(Payment.__table__.select().where(Payment.id == payment_id))
    if not row:
        raise HTTPException(status_code=404, detail="Payment not found")
    return PaymentResponse(
        id=row["id"],
        order_id=row["order_id"],
        amount=row["amount"],
        status=row["status"] or "pending"
    )

@app.put("/payments/{payment_id}", response_model=PaymentResponse)
async def update_payment(payment_id: int, payload: PaymentUpdate):
    existing = await database.fetch_one(Payment.__table__.select().where(Payment.id == payment_id))
    if not existing:
        raise HTTPException(status_code=404, detail="Payment not found")
    await database.execute(Payment.__table__.update().where(Payment.id == payment_id).values(**payload.dict()))
    return PaymentResponse(id=payment_id, **payload.dict())

@app.delete("/payments/{payment_id}", status_code=204)
async def delete_payment(payment_id: int):
    existing = await database.fetch_one(Payment.__table__.select().where(Payment.id == payment_id))
    if not existing:
        raise HTTPException(status_code=404, detail="Payment not found")
    await database.execute(Payment.__table__.delete().where(Payment.id == payment_id))
    return

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
