from pydantic import BaseModel
from typing import Optional
from datetime import time, datetime

class ClinicBase(BaseModel):
    clinic_name: str
    clinic_address: str
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class ClinicCreate(ClinicBase):
    doctor_id: int
    opening_time: Optional[time] = None
    closing_time: Optional[time] = None
    working_days: Optional[str] = None  # JSON string
    is_primary: bool = False

class ClinicUpdate(BaseModel):
    clinic_name: Optional[str] = None
    clinic_address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    opening_time: Optional[time] = None
    closing_time: Optional[time] = None
    working_days: Optional[str] = None
    is_primary: Optional[bool] = None
    is_active: Optional[bool] = None

class ClinicResponse(ClinicBase):
    id: int
    clinic_id: str
    doctor_id: int
    opening_time: Optional[time]
    closing_time: Optional[time]
    working_days: Optional[str]
    clinic_image_path: Optional[str]
    is_primary: bool
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True
