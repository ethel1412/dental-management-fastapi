from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum

class Gender(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"

class Patient(Base):
    __tablename__ = "patients"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    patient_id = Column(String(20), unique=True, nullable=False, index=True)
    full_name = Column(String(100), nullable=False)
    date_of_birth = Column(Date)
    age = Column(Integer)
    gender = Column(Enum(Gender))
    address = Column(Text)
    pincode = Column(String(10))
    profile_image_path = Column(String(500))
    consent_given = Column(Boolean, default=False)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", backref="patient_profile")
    appointments = relationship("Appointment", back_populates="patient")
    clinical_profiles = relationship("ClinicalProfile", back_populates="patient")
