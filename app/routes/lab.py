from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models.user import User, UserRole
from app.models.lab import Lab, LabType
from app.schemas.lab import LabCreate, LabUpdate, LabResponse
from app.services.auth_service import AuthService
from app.services.file_service import FileService
from app.utils.dependencies import get_current_user, require_role
from app.utils.security import generate_unique_id

router = APIRouter(prefix="/api/labs", tags=["Labs"])

@router.post("/register", response_model=dict)
def register_lab(lab_data: LabCreate, db: Session = Depends(get_db)):
    """Register a new lab"""
    # Register user first
    user = AuthService.register_user(
        db=db,
        mobile_number=lab_data.mobile_number,
        email=lab_data.email,
        password=lab_data.password,
        role=UserRole.LAB
    )
    
    # Check if license number exists
    existing_lab = db.query(Lab).filter(
        Lab.license_number == lab_data.license_number
    ).first()
    
    if existing_lab:
        db.delete(user)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="License number already exists"
        )
    
    # Generate lab ID
    last_lab = db.query(Lab).order_by(Lab.id.desc()).first()
    lab_id = generate_unique_id("LAB", last_lab.id if last_lab else None)
    
    # Create lab profile
    new_lab = Lab(
        user_id=user.id,
        lab_id=lab_id,
        lab_name=lab_data.lab_name,
        lab_type=lab_data.lab_type,
        owner_name=lab_data.owner_name,
        lab_address=lab_data.lab_address,
        city=lab_data.city,
        state=lab_data.state,
        pincode=lab_data.pincode,
        latitude=lab_data.latitude,
        longitude=lab_data.longitude,
        license_number=lab_data.license_number,
        gst_number=lab_data.gst_number,
        working_hours=lab_data.working_hours,
        working_days=lab_data.working_days,
        services_offered=lab_data.services_offered,
        pickup_available=lab_data.pickup_available,
        delivery_available=lab_data.delivery_available,
        delivery_mode=lab_data.delivery_mode,
        service_radius_km=lab_data.service_radius_km,
        service_pincodes=lab_data.service_pincodes,
        pickup_time_slots=lab_data.pickup_time_slots,
        delivery_charges=lab_data.delivery_charges,
        free_delivery=lab_data.free_delivery,
        upi_id=lab_data.upi_id,
        account_holder_name=lab_data.account_holder_name,
        account_number=lab_data.account_number,
        ifsc_code=lab_data.ifsc_code,
        settlement_frequency=lab_data.settlement_frequency
    )
    
    db.add(new_lab)
    db.commit()
    db.refresh(new_lab)
    
    return {
        "message": "Lab registered successfully. Please verify OTP",
        "otp": user.otp,
        "lab_id": new_lab.lab_id,
        "user_id": user.id
    }

@router.get("/profile", response_model=LabResponse)
def get_lab_profile(current_user: User = Depends(require_role([UserRole.LAB]))):
    """Get current lab's profile"""
    lab = current_user.lab_profile
    if not lab:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lab profile not found"
        )
    return lab

@router.put("/profile", response_model=LabResponse)
def update_lab_profile(
    lab_update: LabUpdate,
    current_user: User = Depends(require_role([UserRole.LAB])),
    db: Session = Depends(get_db)
):
    """Update lab profile"""
    lab = current_user.lab_profile
    if not lab:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lab profile not found"
        )
    
    update_data = lab_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(lab, field, value)
    
    db.commit()
    db.refresh(lab)
    return lab

@router.post("/upload-certificate")
async def upload_registration_certificate(
    file: UploadFile = File(...),
    current_user: User = Depends(require_role([UserRole.LAB])),
    db: Session = Depends(get_db)
):
    """Upload registration certificate"""
    lab = current_user.lab_profile
    if not lab:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lab profile not found"
        )
    
    file_path = await FileService.save_file(file, "certificates", f"lab_cert_{lab.lab_id}")
    lab.registration_certificate_path = file_path
    db.commit()
    
    return {
        "message": "Registration certificate uploaded successfully",
        "file_path": FileService.get_file_url(file_path)
    }

@router.post("/upload-image")
async def upload_lab_image(
    file: UploadFile = File(...),
    current_user: User = Depends(require_role([UserRole.LAB])),
    db: Session = Depends(get_db)
):
    """Upload lab image"""
    lab = current_user.lab_profile
    if not lab:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lab profile not found"
        )
    
    file_path = await FileService.save_file(file, "profile_images", f"lab_{lab.lab_id}")
    lab.lab_image_path = file_path
    db.commit()
    
    return {
        "message": "Lab image uploaded successfully",
        "file_path": FileService.get_file_url(file_path)
    }

@router.get("/search", response_model=List[LabResponse])
def search_labs(
    lab_type: Optional[LabType] = None,
    city: Optional[str] = None,
    pincode: Optional[str] = None,
    service: Optional[str] = None,
    page: int = 1,
    per_page: int = 10,
    db: Session = Depends(get_db)
):
    """Search labs with filters"""
    query = db.query(Lab).filter(Lab.is_active == True)
    
    if lab_type:
        query = query.filter(Lab.lab_type == lab_type)
    
    if city:
        query = query.filter(Lab.city.ilike(f"%{city}%"))
    
    if pincode:
        query = query.filter(Lab.pincode == pincode)
    
    if service:
        query = query.filter(Lab.services_offered.contains(service))
    
    offset = (page - 1) * per_page
    labs = query.offset(offset).limit(per_page).all()
    
    return labs

@router.get("/{lab_id}", response_model=LabResponse)
def get_lab_by_id(lab_id: str, db: Session = Depends(get_db)):
    """Get lab by ID"""
    lab = db.query(Lab).filter(Lab.lab_id == lab_id).first()
    if not lab:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lab not found"
        )
    return lab
