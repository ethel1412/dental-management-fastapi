from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.user import User, UserRole
from app.models.clinic import Clinic
from app.schemas.clinic import ClinicCreate, ClinicUpdate, ClinicResponse
from app.services.file_service import FileService
from app.utils.dependencies import require_role
from app.utils.security import generate_unique_id

router = APIRouter(prefix="/api/clinics", tags=["Clinics"])

@router.post("/", response_model=ClinicResponse)
def create_clinic(
    clinic_data: ClinicCreate,
    current_user: User = Depends(require_role([UserRole.DOCTOR])),
    db: Session = Depends(get_db)
):
    """Create a new clinic"""
    doctor = current_user.doctor_profile
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor profile not found"
        )
    
    # Generate clinic ID
    last_clinic = db.query(Clinic).order_by(Clinic.id.desc()).first()
    clinic_id = generate_unique_id("CLN", last_clinic.id if last_clinic else None)
    
    # If this is primary, unset other primary clinics
    if clinic_data.is_primary:
        db.query(Clinic).filter(
            Clinic.doctor_id == doctor.id,
            Clinic.is_primary == True
        ).update({"is_primary": False})
    
    new_clinic = Clinic(
        doctor_id=doctor.id,
        clinic_id=clinic_id,
        clinic_name=clinic_data.clinic_name,
        clinic_address=clinic_data.clinic_address,
        city=clinic_data.city,
        state=clinic_data.state,
        pincode=clinic_data.pincode,
        latitude=clinic_data.latitude,
        longitude=clinic_data.longitude,
        opening_time=clinic_data.opening_time,
        closing_time=clinic_data.closing_time,
        working_days=clinic_data.working_days,
        is_primary=clinic_data.is_primary
    )
    
    db.add(new_clinic)
    db.commit()
    db.refresh(new_clinic)
    
    return new_clinic

@router.get("/my-clinics", response_model=List[ClinicResponse])
def get_my_clinics(
    current_user: User = Depends(require_role([UserRole.DOCTOR])),
    db: Session = Depends(get_db)
):
    """Get all clinics of current doctor"""
    doctor = current_user.doctor_profile
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor profile not found"
        )
    
    clinics = db.query(Clinic).filter(
        Clinic.doctor_id == doctor.id,
        Clinic.is_active == True
    ).all()
    
    return clinics

@router.get("/{clinic_id}", response_model=ClinicResponse)
def get_clinic(clinic_id: str, db: Session = Depends(get_db)):
    """Get clinic by ID"""
    clinic = db.query(Clinic).filter(Clinic.clinic_id == clinic_id).first()
    if not clinic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clinic not found"
        )
    return clinic

@router.put("/{clinic_id}", response_model=ClinicResponse)
def update_clinic(
    clinic_id: str,
    clinic_update: ClinicUpdate,
    current_user: User = Depends(require_role([UserRole.DOCTOR])),
    db: Session = Depends(get_db)
):
    """Update clinic"""
    doctor = current_user.doctor_profile
    clinic = db.query(Clinic).filter(Clinic.clinic_id == clinic_id).first()
    
    if not clinic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clinic not found"
        )
    
    if clinic.doctor_id != doctor.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Update fields
    update_data = clinic_update.dict(exclude_unset=True)
    
    # If setting as primary, unset others
    if update_data.get("is_primary"):
        db.query(Clinic).filter(
            Clinic.doctor_id == doctor.id,
            Clinic.id != clinic.id,
            Clinic.is_primary == True
        ).update({"is_primary": False})
    
    for field, value in update_data.items():
        setattr(clinic, field, value)
    
    db.commit()
    db.refresh(clinic)
    return clinic

@router.delete("/{clinic_id}")
def delete_clinic(
    clinic_id: str,
    current_user: User = Depends(require_role([UserRole.DOCTOR])),
    db: Session = Depends(get_db)
):
    """Delete (deactivate) clinic"""
    doctor = current_user.doctor_profile
    clinic = db.query(Clinic).filter(Clinic.clinic_id == clinic_id).first()
    
    if not clinic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clinic not found"
        )
    
    if clinic.doctor_id != doctor.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    clinic.is_active = False
    db.commit()
    
    return {"message": "Clinic deactivated successfully"}

@router.post("/{clinic_id}/upload-image")
async def upload_clinic_image(
    clinic_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(require_role([UserRole.DOCTOR])),
    db: Session = Depends(get_db)
):
    """Upload clinic image"""
    doctor = current_user.doctor_profile
    clinic = db.query(Clinic).filter(Clinic.clinic_id == clinic_id).first()
    
    if not clinic or clinic.doctor_id != doctor.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clinic not found"
        )
    
    file_path = await FileService.save_file(file, "profile_images", f"clinic_{clinic_id}")
    clinic.clinic_image_path = file_path
    db.commit()
    
    return {
        "message": "Clinic image uploaded successfully",
        "file_path": FileService.get_file_url(file_path)
    }
