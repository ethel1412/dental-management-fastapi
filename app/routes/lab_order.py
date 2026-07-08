from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import status as http_status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models.user import User, UserRole
from app.models.lab_order import LabOrder, OrderStatus
from app.models.doctor import Doctor
from app.models.lab import Lab
from app.schemas.lab_order import LabOrderCreate, LabOrderUpdate, LabOrderResponse
from app.utils.dependencies import get_current_user
from app.utils.security import generate_unique_id

router = APIRouter(prefix="/api/lab-orders", tags=["Lab Orders"])


@router.post("", response_model=LabOrderResponse)
def create_lab_order(
    order_data: LabOrderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new lab order (doctor only)"""
    if current_user.role != UserRole.DOCTOR:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="Only doctors can create lab orders"
        )

    doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
    if not doctor:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Doctor profile not found"
        )

    new_order = LabOrder(
        id=generate_unique_id(),
        doctor_id=doctor.id,
        lab_id=order_data.lab_id,
        patient_name=order_data.patient_name,
        patient_age=order_data.patient_age,
        test_type=order_data.test_type,
        description=order_data.description,
        priority=order_data.priority,
        status=OrderStatus.PENDING
    )

    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    return new_order


@router.get("/my-orders", response_model=List[LabOrderResponse])
def get_my_orders(
    order_status: Optional[OrderStatus] = Query(None, alias="status"),
    page: int = 1,
    per_page: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get orders for current user (doctor or lab)"""
    query = db.query(LabOrder)

    if current_user.role == UserRole.DOCTOR:
        doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
        if not doctor:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="Doctor profile not found"
            )
        query = query.filter(LabOrder.doctor_id == doctor.id)

    elif current_user.role == UserRole.LAB:
        lab = db.query(Lab).filter(Lab.user_id == current_user.id).first()
        if not lab:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="Lab profile not found"
            )
        query = query.filter(LabOrder.lab_id == lab.id)

    else:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    if order_status:
        query = query.filter(LabOrder.status == order_status)

    query = query.order_by(LabOrder.created_at.desc())

    offset = (page - 1) * per_page
    orders = query.offset(offset).limit(per_page).all()

    return orders


@router.get("/{order_id}", response_model=LabOrderResponse)
def get_order(
    order_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific lab order"""
    order = db.query(LabOrder).filter(LabOrder.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    return order


@router.put("/{order_id}", response_model=LabOrderResponse)
def update_order(
    order_id: str,
    update_data: LabOrderUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update lab order status or details"""
    order = db.query(LabOrder).filter(LabOrder.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    update_dict = update_data.dict(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(order, field, value)

    db.commit()
    db.refresh(order)
    return order
