from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, Float, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum

class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    IN_PROGRESS = "in_progress"
    READY = "ready"
    PICKED_UP = "picked_up"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

class LabOrder(Base):
    __tablename__ = "lab_orders"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String(20), unique=True, nullable=False, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    lab_id = Column(Integer, ForeignKey("labs.id"), nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    clinical_profile_id = Column(Integer, ForeignKey("clinical_profiles.id"))
    
    # Order Details
    service_type = Column(String(200), nullable=False)
    description = Column(Text)
    special_instructions = Column(Text)
    
    # Files
    prescription_path = Column(String(500))
    stl_file_path = Column(String(500))
    reference_images = Column(Text)  # JSON array of paths
    
    # Status & Tracking
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)
    estimated_delivery_date = Column(Date)
    actual_delivery_date = Column(Date)
    
    # Logistics
    pickup_requested = Column(Boolean, default=False)
    pickup_date = Column(Date)
    pickup_time_slot = Column(String(50))
    pickup_address = Column(Text)
    delivery_requested = Column(Boolean, default=False)
    delivery_address = Column(Text)
    
    # Pricing
    quoted_price = Column(Float)
    final_price = Column(Float)
    delivery_charges = Column(Float, default=0.0)
    
    # Lab Response
    lab_notes = Column(Text)
    result_file_path = Column(String(500))
    result_images = Column(Text)  # JSON array
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    lab = relationship("Lab", back_populates="lab_orders")
