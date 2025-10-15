from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, Time, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum

class AppointmentStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"

class Appointment(Base):
    __tablename__ = "appointments"
    
    id = Column(Integer, primary_key=True, index=True)
    appointment_id = Column(String(20), unique=True, nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    clinic_id = Column(Integer, ForeignKey("clinics.id"), nullable=False)
    
    appointment_date = Column(Date, nullable=False)
    appointment_time = Column(Time, nullable=False)
    duration_minutes = Column(Integer, default=30)
    reason = Column(Text)
    status = Column(Enum(AppointmentStatus), default=AppointmentStatus.SCHEDULED)
    notes = Column(Text)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    patient = relationship("Patient", back_populates="appointments")
    doctor = relationship("Doctor", back_populates="appointments")
    clinic = relationship("Clinic", back_populates="appointments")
    clinical_profile = relationship("ClinicalProfile", back_populates="appointment", uselist=False)
