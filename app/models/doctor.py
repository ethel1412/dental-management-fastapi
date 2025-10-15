from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Text, ForeignKey, Time
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Doctor(Base):
    __tablename__ = "doctors"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    doctor_id = Column(String(20), unique=True, nullable=False, index=True)
    full_name = Column(String(100), nullable=False)
    specialization = Column(String(100), nullable=False)
    years_of_experience = Column(Integer)
    dci_registration_number = Column(String(50), unique=True, nullable=False)
    
    # Qualifications
    qualification_bds = Column(String(200))
    qualification_mds = Column(String(200))
    qualification_fellowship = Column(String(200))
    other_qualifications = Column(Text)
    
    # Consultation
    consultation_fee_online = Column(Float)
    consultation_fee_offline = Column(Float)
    
    # Verification
    dci_certificate_path = Column(String(500))
    govt_id_path = Column(String(500))
    profile_image_path = Column(String(500))
    
    # Bank Details
    account_holder_name = Column(String(100))
    account_number = Column(String(50))
    ifsc_code = Column(String(20))
    upi_id = Column(String(100))
    
    # Availability
    online_consultation_available = Column(Boolean, default=False)
    available_days = Column(String(200))
    booking_limit_per_day = Column(Integer, default=10)
    
    # Services
    services_offered = Column(Text)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", backref="doctor_profile")
    clinics = relationship("Clinic", back_populates="doctor")
    appointments = relationship("Appointment", back_populates="doctor")
    
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "doctor_id": self.doctor_id,
            "full_name": self.full_name,
            "specialization": self.specialization,
            "years_of_experience": self.years_of_experience,
            "dci_registration_number": self.dci_registration_number,
            "qualification_bds": self.qualification_bds,
            "qualification_mds": self.qualification_mds,
            "other_qualifications": self.other_qualifications,
            "consultation_fee_online": self.consultation_fee_online,
            "consultation_fee_offline": self.consultation_fee_offline,
            "profile_image_path": self.profile_image_path,
            "is_active": self.is_active
        }
