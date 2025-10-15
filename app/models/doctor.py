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
    available_days = Column(String(200))  # JSON string
    booking_limit_per_day = Column(Integer, default=10)
    
    # Services (stored as JSON string)
    services_offered = Column(Text)  # JSON array
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", backref="doctor_profile")
    clinics = relationship("Clinic", back_populates="doctor")
    appointments = relationship("Appointment", back_populates="doctor")
