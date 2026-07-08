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
    # uselist=False makes user.patient_profile return a single Patient (or None),
    # not a list. This is correct because user_id is unique (one-to-one).
    user = relationship("User", backref="patient_profile")
    appointments = relationship("Appointment", back_populates="patient")
    clinical_profiles = relationship("ClinicalProfile", back_populates="patient")

    def to_dict(self):
        """Convert patient object to dictionary"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "patient_id": self.patient_id,
            "full_name": self.full_name,
            "date_of_birth": self.date_of_birth.isoformat() if self.date_of_birth else None,
            "age": self.age,
            "gender": self.gender.value if self.gender else None,
            "address": self.address,
            "pincode": self.pincode,
            "profile_image_path": self.profile_image_path,
            "consent_given": self.consent_given,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
