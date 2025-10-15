from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class DoctorBase(BaseModel):
    full_name: str
    specialization: str
    years_of_experience: Optional[int] = None
    dci_registration_number: str

class DoctorCreate(DoctorBase):
    mobile_number: str
    email: Optional[str] = None
    password: str
    qualification_bds: Optional[str] = None
    qualification_mds: Optional[str] = None
    qualification_fellowship: Optional[str] = None
    other_qualifications: Optional[str] = None
    consultation_fee_online: Optional[float] = None
    consultation_fee_offline: Optional[float] = None
    online_consultation_available: bool = False
    available_days: Optional[str] = None  # JSON string
    booking_limit_per_day: int = 10
    services_offered: Optional[str] = None  # JSON string
    account_holder_name: Optional[str] = None
    account_number: Optional[str] = None
    ifsc_code: Optional[str] = None
    upi_id: Optional[str] = None

class DoctorUpdate(BaseModel):
    full_name: Optional[str] = None
    specialization: Optional[str] = None
    years_of_experience: Optional[int] = None
    qualification_bds: Optional[str] = None
    qualification_mds: Optional[str] = None
    qualification_fellowship: Optional[str] = None
    other_qualifications: Optional[str] = None
    consultation_fee_online: Optional[float] = None
    consultation_fee_offline: Optional[float] = None
    online_consultation_available: Optional[bool] = None
    available_days: Optional[str] = None
    booking_limit_per_day: Optional[int] = None
    services_offered: Optional[str] = None
    account_holder_name: Optional[str] = None
    account_number: Optional[str] = None
    ifsc_code: Optional[str] = None
    upi_id: Optional[str] = None

class DoctorResponse(DoctorBase):
    id: int
    doctor_id: str
    user_id: int
    qualification_bds: Optional[str]
    qualification_mds: Optional[str]
    qualification_fellowship: Optional[str]
    other_qualifications: Optional[str]
    consultation_fee_online: Optional[float]
    consultation_fee_offline: Optional[float]
    dci_certificate_path: Optional[str]
    govt_id_path: Optional[str]
    profile_image_path: Optional[str]
    online_consultation_available: bool
    available_days: Optional[str]
    booking_limit_per_day: int
    services_offered: Optional[str]
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class DoctorSearchFilters(BaseModel):
    specialization: Optional[str] = None
    city: Optional[str] = None
    pincode: Optional[str] = None
    availability_date: Optional[str] = None
    online_consultation: Optional[bool] = None
    max_fee: Optional[float] = None
    page: int = 1
    per_page: int = 10
