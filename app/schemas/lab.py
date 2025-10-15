from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.lab import LabType, DeliveryMode

class LabBase(BaseModel):
    lab_name: str
    lab_type: LabType
    owner_name: str
    lab_address: str
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None

class LabCreate(LabBase):
    mobile_number: str
    email: Optional[str] = None
    password: str
    license_number: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    gst_number: Optional[str] = None
    working_hours: Optional[str] = None  # JSON
    working_days: Optional[str] = None  # JSON
    services_offered: Optional[str] = None  # JSON
    pickup_available: bool = True
    delivery_available: bool = True
    delivery_mode: Optional[DeliveryMode] = None
    service_radius_km: Optional[int] = None
    service_pincodes: Optional[str] = None  # JSON
    pickup_time_slots: Optional[str] = None  # JSON
    delivery_charges: float = 0.0
    free_delivery: bool = False
    upi_id: Optional[str] = None
    account_holder_name: Optional[str] = None
    account_number: Optional[str] = None
    ifsc_code: Optional[str] = None
    settlement_frequency: Optional[str] = None

class LabUpdate(BaseModel):
    lab_name: Optional[str] = None
    owner_name: Optional[str] = None
    lab_address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    working_hours: Optional[str] = None
    working_days: Optional[str] = None
    services_offered: Optional[str] = None
    pickup_available: Optional[bool] = None
    delivery_available: Optional[bool] = None
    delivery_mode: Optional[DeliveryMode] = None
    service_radius_km: Optional[int] = None
    service_pincodes: Optional[str] = None
    delivery_charges: Optional[float] = None
    free_delivery: Optional[bool] = None

class LabResponse(LabBase):
    id: int
    lab_id: str
    user_id: int
    license_number: str
    registration_certificate_path: Optional[str]
    lab_image_path: Optional[str]
    gst_number: Optional[str]
    working_hours: Optional[str]
    working_days: Optional[str]
    services_offered: Optional[str]
    pickup_available: bool
    delivery_available: bool
    delivery_mode: Optional[DeliveryMode]
    service_radius_km: Optional[int]
    service_pincodes: Optional[str]
    delivery_charges: float
    free_delivery: bool
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True
