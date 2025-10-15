from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime
from app.models.lab_order import OrderStatus

class LabOrderBase(BaseModel):
    service_type: str
    description: Optional[str] = None
    special_instructions: Optional[str] = None

class LabOrderCreate(LabOrderBase):
    lab_id: int
    patient_id: int
    clinical_profile_id: Optional[int] = None
    pickup_requested: bool = False
    pickup_date: Optional[date] = None
    pickup_time_slot: Optional[str] = None
    pickup_address: Optional[str] = None
    delivery_requested: bool = False
    delivery_address: Optional[str] = None

class LabOrderUpdate(BaseModel):
    status: Optional[OrderStatus] = None
    estimated_delivery_date: Optional[date] = None
    quoted_price: Optional[float] = None
    final_price: Optional[float] = None
    delivery_charges: Optional[float] = None
    lab_notes: Optional[str] = None

class LabOrderResponse(LabOrderBase):
    id: int
    order_id: str
    doctor_id: int
    lab_id: int
    patient_id: int
    clinical_profile_id: Optional[int]
    status: OrderStatus
    estimated_delivery_date: Optional[date]
    actual_delivery_date: Optional[date]
    prescription_path: Optional[str]
    stl_file_path: Optional[str]
    reference_images: Optional[str]
    quoted_price: Optional[float]
    final_price: Optional[float]
    result_file_path: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True
