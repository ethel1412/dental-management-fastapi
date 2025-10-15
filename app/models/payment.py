from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum

class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"

class PaymentType(str, enum.Enum):
    CONSULTATION = "consultation"
    LAB_ORDER = "lab_order"
    TREATMENT = "treatment"

class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    payment_id = Column(String(20), unique=True, nullable=False, index=True)
    payment_type = Column(Enum(PaymentType), nullable=False)
    
    # References
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("doctors.id"))
    lab_id = Column(Integer, ForeignKey("labs.id"))
    appointment_id = Column(Integer, ForeignKey("appointments.id"))
    lab_order_id = Column(Integer, ForeignKey("lab_orders.id"))
    
    # Payment Details
    amount = Column(Float, nullable=False)
    payment_method = Column(String(50))  # dummy_cash, dummy_card, dummy_upi
    transaction_id = Column(String(100))
    status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING)
    payment_date = Column(DateTime)
    
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
