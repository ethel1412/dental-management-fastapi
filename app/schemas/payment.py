from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.payment import PaymentStatus, PaymentType

class PaymentCreate(BaseModel):
    payment_type: PaymentType
    doctor_id: Optional[int] = None
    lab_id: Optional[int] = None
    appointment_id: Optional[int] = None
    lab_order_id: Optional[int] = None
    amount: float
    payment_method: str  # dummy_cash, dummy_card, dummy_upi

class PaymentResponse(BaseModel):
    id: int
    payment_id: str
    payment_type: PaymentType
    patient_id: int
    doctor_id: Optional[int]
    lab_id: Optional[int]
    amount: float
    payment_method: str
    transaction_id: Optional[str]
    status: PaymentStatus
    payment_date: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True
