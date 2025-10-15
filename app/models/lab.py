from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum

class LabType(str, enum.Enum):
    DENTAL = "dental"
    DIAGNOSTIC = "diagnostic"

class DeliveryMode(str, enum.Enum):
    INHOUSE = "inhouse"
    THIRD_PARTY = "third_party"
    COURIER = "courier"

class Lab(Base):
    __tablename__ = "labs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    lab_id = Column(String(20), unique=True, nullable=False, index=True)
    lab_name = Column(String(200), nullable=False)
    lab_type = Column(Enum(LabType), nullable=False)
    owner_name = Column(String(100), nullable=False)
    
    # Address
    lab_address = Column(Text, nullable=False)
    city = Column(String(100))
    state = Column(String(100))
    pincode = Column(String(10))
    latitude = Column(Float)
    longitude = Column(Float)
    
    # Registration
    license_number = Column(String(100), unique=True, nullable=False)
    registration_certificate_path = Column(String(500))
    lab_image_path = Column(String(500))
    gst_number = Column(String(20))
    
    # Working Hours
    working_hours = Column(String(200))  # JSON string
    working_days = Column(String(200))  # JSON string
    
    # Services (JSON array)
    services_offered = Column(Text)
    
    # Logistics
    pickup_available = Column(Boolean, default=True)
    delivery_available = Column(Boolean, default=True)
    delivery_mode = Column(Enum(DeliveryMode))
    service_radius_km = Column(Integer)
    service_pincodes = Column(Text)  # JSON array
    pickup_time_slots = Column(String(200))  # JSON string
    delivery_charges = Column(Float, default=0.0)
    free_delivery = Column(Boolean, default=False)
    
    # Payment
    upi_id = Column(String(100))
    account_holder_name = Column(String(100))
    account_number = Column(String(50))
    ifsc_code = Column(String(20))
    settlement_frequency = Column(String(20))  # instant, weekly, monthly
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", backref="lab_profile")
    lab_orders = relationship("LabOrder", back_populates="lab")

    def to_dict(self):
        """Convert lab object to dictionary"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "lab_id": self.lab_id,
            "lab_name": self.lab_name,
            "lab_type": self.lab_type.value if self.lab_type else None,
            "owner_name": self.owner_name,
            "lab_address": self.lab_address,
            "city": self.city,
            "state": self.state,
            "pincode": self.pincode,
            "license_number": self.license_number,
            "pickup_available": self.pickup_available,
            "delivery_available": self.delivery_available,
            "free_delivery": self.free_delivery,
            "registration_certificate_path": self.registration_certificate_path,
            "lab_image_path": self.lab_image_path,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
