from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from app.database import get_db
from app.models.user import User, UserRole
from app.models.payment import Payment, PaymentStatus, PaymentType
from app.schemas.payment import PaymentCreate, PaymentResponse
from app.utils.dependencies import get_current_user, require_role
from app.utils.security import generate_unique_id
import random
import string

router = APIRouter(prefix="/api/payments", tags=["Payments"])

def generate_transaction_id():
    """Generate dummy transaction ID"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))

@router.post("/", response_model=PaymentResponse)
def create_payment(
    payment_data: PaymentCreate,
    current_user: User = Depends(require_role([UserRole.PATIENT])),
    db: Session = Depends(get_db)
):
    """Create a dummy payment"""
    patient = current_user.patient_profile
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient profile not found"
        )
    
    # Generate payment ID
    last_payment = db.query(Payment).order_by(Payment.id.desc()).first()
    payment_id = generate_unique_id("PAY", last_payment.id if last_payment else None)
    
    # Generate dummy transaction ID
    transaction_id = generate_transaction_id()
    
    # Create payment (dummy - always successful)
    new_payment = Payment(
        payment_id=payment_id,
        payment_type=payment_data.payment_type,
        patient_id=patient.id,
        doctor_id=payment_data.doctor_id,
        lab_id=payment_data.lab_id,
        appointment_id=payment_data.appointment_id,
        lab_order_id=payment_data.lab_order_id,
        amount=payment_data.amount,
        payment_method=payment_data.payment_method,
        transaction_id=transaction_id,
        status=PaymentStatus.COMPLETED,
        payment_date=datetime.utcnow()
    )
    
    db.add(new_payment)
    db.commit()
    db.refresh(new_payment)
    
    return new_payment

@router.get("/my-payments", response_model=List[PaymentResponse])
def get_my_payments(
    page: int = 1,
    per_page: int = 10,
    current_user: User = Depends(require_role([UserRole.PATIENT])),
    db: Session = Depends(get_db)
):
    """Get payment history for patient"""
    patient = current_user.patient_profile
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient profile not found"
        )
    
    query = db.query(Payment).filter(Payment.patient_id == patient.id)
    query = query.order_by(Payment.created_at.desc())
    
    offset = (page - 1) * per_page
    payments = query.offset(offset).limit(per_page).all()
    
    return payments

@router.get("/{payment_id}", response_model=PaymentResponse)
def get_payment(
    payment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get payment by ID"""
    payment = db.query(Payment).filter(Payment.payment_id == payment_id).first()
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    # Check access
    if current_user.role == UserRole.PATIENT:
        patient = current_user.patient_profile
        if not patient or payment.patient_id != patient.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    elif current_user.role == UserRole.DOCTOR:
        doctor = current_user.doctor_profile
        if not doctor or payment.doctor_id != doctor.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    elif current_user.role == UserRole.LAB:
        lab = current_user.lab_profile
        if not lab or payment.lab_id != lab.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    
    return payment

@router.get("/doctor/earnings")
def get_doctor_earnings(
    current_user: User = Depends(require_role([UserRole.DOCTOR])),
    db: Session = Depends(get_db)
):
    """Get earnings summary for doctor"""
    doctor = current_user.doctor_profile
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor profile not found"
        )
    
    from sqlalchemy import func
    
    # Total earnings
    total_earnings = db.query(func.sum(Payment.amount)).filter(
        Payment.doctor_id == doctor.id,
        Payment.status == PaymentStatus.COMPLETED
    ).scalar() or 0.0
    
    # Count of payments
    payment_count = db.query(func.count(Payment.id)).filter(
        Payment.doctor_id == doctor.id,
        Payment.status == PaymentStatus.COMPLETED
    ).scalar() or 0
    
    # Recent payments
    recent_payments = db.query(Payment).filter(
        Payment.doctor_id == doctor.id
    ).order_by(Payment.created_at.desc()).limit(5).all()
    
    return {
        "total_earnings": float(total_earnings),
        "payment_count": payment_count,
        "recent_payments": recent_payments
    }

@router.get("/lab/earnings")
def get_lab_earnings(
    current_user: User = Depends(require_role([UserRole.LAB])),
    db: Session = Depends(get_db)
):
    """Get earnings summary for lab"""
    lab = current_user.lab_profile
    if not lab:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lab profile not found"
        )
    
    from sqlalchemy import func
    
    # Total earnings
    total_earnings = db.query(func.sum(Payment.amount)).filter(
        Payment.lab_id == lab.id,
        Payment.status == PaymentStatus.COMPLETED
    ).scalar() or 0.0
    
    # Count of payments
    payment_count = db.query(func.count(Payment.id)).filter(
        Payment.lab_id == lab.id,
        Payment.status == PaymentStatus.COMPLETED
    ).scalar() or 0
    
    # Recent payments
    recent_payments = db.query(Payment).filter(
        Payment.lab_id == lab.id
    ).order_by(Payment.created_at.desc()).limit(5).all()
    
    return {
        "total_earnings": float(total_earnings),
        "payment_count": payment_count,
        "recent_payments": recent_payments
    }
