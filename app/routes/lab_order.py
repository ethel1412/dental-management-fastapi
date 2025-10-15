from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models.user import User, UserRole
from app.models.lab_order import LabOrder, OrderStatus
from app.schemas.lab_order import LabOrderCreate, LabOrderUpdate, LabOrderResponse
from app.services.file_service import FileService
from app.utils.dependencies import get_current_user, require_role
from app.utils.security import generate_unique_id

router = APIRouter(prefix="/api/lab-orders", tags=["Lab Orders"])

@router.post("/", response_model=LabOrderResponse)
def create_lab_order(
    order_data: LabOrderCreate,
    current_user: User = Depends(require_role([UserRole.DOCTOR])),
    db: Session = Depends(get_db)
):
    """Create a new lab order (doctor orders from lab)"""
    doctor = current_user.doctor_profile
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor profile not found"
        )
    
    # Generate order ID
    last_order = db.query(LabOrder).order_by(LabOrder.id.desc()).first()
    order_id = generate_unique_id("LO", last_order.id if last_order else None)
    
    # Create order
    new_order = LabOrder(
        order_id=order_id,
        doctor_id=doctor.id,
        lab_id=order_data.lab_id,
        patient_id=order_data.patient_id,
        clinical_profile_id=order_data.clinical_profile_id,
        service_type=order_data.service_type,
        description=order_data.description,
        special_instructions=order_data.special_instructions,
        pickup_requested=order_data.pickup_requested,
        pickup_date=order_data.pickup_date,
        pickup_time_slot=order_data.pickup_time_slot,
        pickup_address=order_data.pickup_address,
        delivery_requested=order_data.delivery_requested,
        delivery_address=order_data.delivery_address,
        status=OrderStatus.PENDING
    )
    
    db.add(new_order)
    db.commit()
    db.refresh(new_order)
    
    return new_order

@router.get("/my-orders", response_model=List[LabOrderResponse])
def get_my_orders(
    status: Optional[OrderStatus] = None,
    page: int = 1,
    per_page: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get orders for current user (doctor or lab)"""
    query = db.query(LabOrder)
    
    if current_user.role == UserRole.DOCTOR:
        doctor = current_user.doctor_profile
        if not doctor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Doctor profile not found"
            )
        query = query.filter(LabOrder.doctor_id == doctor.id)
    
    elif current_user.role == UserRole.LAB:
        lab = current_user.lab_profile
        if not lab:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lab profile not found"
            )
        query = query.filter(LabOrder.lab_id == lab.id)
    
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    if status:
        query = query.filter(LabOrder.status == status)
    
    query = query.order_by(LabOrder.created_at.desc())
    
    offset = (page - 1) * per_page
    orders = query.offset(offset).limit(per_page).all()
    
    return orders

@router.get("/{order_id}", response_model=LabOrderResponse)
def get_lab_order(
    order_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get lab order by ID"""
    order = db.query(LabOrder).filter(LabOrder.order_id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Check access
    if current_user.role == UserRole.DOCTOR:
        doctor = current_user.doctor_profile
        if not doctor or order.doctor_id != doctor.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    elif current_user.role == UserRole.LAB:
        lab = current_user.lab_profile
        if not lab or order.lab_id != lab.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    
    return order

@router.put("/{order_id}", response_model=LabOrderResponse)
def update_lab_order(
    order_id: str,
    order_update: LabOrderUpdate,
    current_user: User = Depends(require_role([UserRole.LAB])),
    db: Session = Depends(get_db)
):
    """Update lab order (by lab)"""
    lab = current_user.lab_profile
    order = db.query(LabOrder).filter(LabOrder.order_id == order_id).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    if order.lab_id != lab.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    update_data = order_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(order, field, value)
    
    db.commit()
    db.refresh(order)
    return order

@router.post("/{order_id}/upload-prescription")
async def upload_prescription(
    order_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(require_role([UserRole.DOCTOR])),
    db: Session = Depends(get_db)
):
    """Upload prescription for lab order"""
    doctor = current_user.doctor_profile
    order = db.query(LabOrder).filter(LabOrder.order_id == order_id).first()
    
    if not order or order.doctor_id != doctor.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    file_path = await FileService.save_file(file, "reports", f"prescription_{order_id}")
    order.prescription_path = file_path
    db.commit()
    
    return {
        "message": "Prescription uploaded successfully",
        "file_path": FileService.get_file_url(file_path)
    }

@router.post("/{order_id}/upload-stl")
async def upload_stl_file(
    order_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(require_role([UserRole.DOCTOR])),
    db: Session = Depends(get_db)
):
    """Upload STL file for dental lab order"""
    doctor = current_user.doctor_profile
    order = db.query(LabOrder).filter(LabOrder.order_id == order_id).first()
    
    if not order or order.doctor_id != doctor.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    file_path = await FileService.save_file(file, "stl_files", f"stl_{order_id}")
    order.stl_file_path = file_path
    db.commit()
    
    return {
        "message": "STL file uploaded successfully",
        "file_path": FileService.get_file_url(file_path)
    }

@router.post("/{order_id}/upload-result")
async def upload_result(
    order_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(require_role([UserRole.LAB])),
    db: Session = Depends(get_db)
):
    """Upload result/report by lab"""
    lab = current_user.lab_profile
    order = db.query(LabOrder).filter(LabOrder.order_id == order_id).first()
    
    if not order or order.lab_id != lab.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    file_path = await FileService.save_file(file, "reports", f"result_{order_id}")
    order.result_file_path = file_path
    db.commit()
    
    return {
        "message": "Result uploaded successfully",
        "file_path": FileService.get_file_url(file_path)
    }
