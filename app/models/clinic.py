from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float, Time, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Clinic(Base):
    __tablename__ = "clinics"
    
    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    clinic_id = Column(String(20), unique=True, nullable=False, index=True)
    clinic_name = Column(String(200), nullable=False)
    clinic_address = Column(Text, nullable=False)
    city = Column(String(100))
    state = Column(String(100))
    pincode = Column(String(10))
    latitude = Column(Float)
    longitude = Column(Float)
    
    # Timings
    opening_time = Column(Time)
    closing_time = Column(Time)
    working_days = Column(String(200))  # JSON string
    
    clinic_image_path = Column(String(500))
    is_primary = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    doctor = relationship("Doctor", back_populates="clinics")
    appointments = relationship("Appointment", back_populates="clinic")
