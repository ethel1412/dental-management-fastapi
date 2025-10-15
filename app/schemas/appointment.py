from pydantic import BaseModel
from typing import Optional
from datetime import date, time, datetime
from app.models.appointment import AppointmentStatus

class AppointmentBase(BaseModel):
    appointment_date: date
    appointment_time: time
    reason: Optional[str] = None

class AppointmentCreate(AppointmentBase):
    doctor_id: int
    clinic_id: int
    duration_minutes: int = 30

class AppointmentUpdate(BaseModel):
    appointment_date: Optional[date] = None
    appointment_time: Optional[time] = None
    reason: Optional[str] = None
    status: Optional[AppointmentStatus] = None
    notes: Optional[str] = None

class AppointmentResponse(AppointmentBase):
    id: int
    appointment_id: str
    patient_id: int
    doctor_id: int
    clinic_id: int
    duration_minutes: int
    status: AppointmentStatus
    notes: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True
