from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime
from app.models.patient import Gender

class PatientBase(BaseModel):
    full_name: str
    age: Optional[int] = None
    date_of_birth: Optional[date] = None
    gender: Optional[Gender] = None

class PatientCreate(PatientBase):
    mobile_number: str
    email: Optional[str] = None
    password: str
    address: Optional[str] = None
    pincode: Optional[str] = None
    consent_given: bool = False

class PatientUpdate(BaseModel):
    full_name: Optional[str] = None
    age: Optional[int] = None
    date_of_birth: Optional[date] = None
    gender: Optional[Gender] = None
    address: Optional[str] = None
    pincode: Optional[str] = None

class PatientResponse(PatientBase):
    id: int
    patient_id: str
    user_id: int
    address: Optional[str]
    pincode: Optional[str]
    profile_image_path: Optional[str]
    consent_given: bool
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True
