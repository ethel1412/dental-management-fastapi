from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query, Form
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import time
from app.database import get_db
from app.models.user import User, UserRole
from app.models.doctor import Doctor
from app.schemas.doctor import DoctorCreate, DoctorUpdate, DoctorResponse, DoctorSearchFilters
from app.services.auth_service import AuthService
from app.services.file_service import FileService
from app.services.doctor_service import DoctorService
from app.utils.dependencies import get_current_user, require_role
from app.utils.security import generate_unique_id


router = APIRouter(prefix="/api/doctors", tags=["Doctors"])


# NEW: Form-based registration for Flutter app
@router.post("/register", response_model=dict)
async def register_doctor(
    mobile_number: str = Form(...),
    full_name: str = Form(...),
    specialization: str = Form(...),
    years_of_experience: int = Form(...),
    dci_registration_number: str = Form(...),
    qualification_bds: str = Form(...),
    qualification_mds: str = Form(None),
    additional_qualifications: str = Form(None),
    consultation_fee_online: float = Form(...),
    consultation_fee_offline: float = Form(...),
    online_consultation_available: bool = Form(False),
    available_days: str = Form(""),
    booking_limit_per_day: int = Form(10),
    services_offered: str = Form(""),
    profile_image: UploadFile = File(None),
    dci_certificate: UploadFile = File(None),
    govt_id: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    """Register a new doctor"""
    # Check if mobile already registered
    existing_user = db.query(User).filter(User.mobile_number == mobile_number).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mobile number already registered"
        )

    profile_image_path = None
    dci_certificate_path = None
    govt_id_path = None

    os.makedirs(os.path.join("uploads", "profiles"), exist_ok=True)
    os.makedirs(os.path.join("uploads", "certificates"), exist_ok=True)
    os.makedirs(os.path.join("uploads", "govt_ids"), exist_ok=True)

    if profile_image and profile_image.filename:
        file_extension = profile_image.filename.split('.')[-1]
        filename = f"profile_{mobile_number}_{int(time.time())}.{file_extension}"
        file_path = os.path.join("uploads", "profiles", filename)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "wb") as f:
            content = await profile_image.read()
            f.write(content)
        profile_image_path = f"/profiles/{filename}"

    if dci_certificate and dci_certificate.filename:
        file_extension = dci_certificate.filename.split('.')[-1]
        filename = f"dci_{mobile_number}_{int(time.time())}.{file_extension}"
        file_path = os.path.join("uploads", "certificates", filename)
        with open(file_path, "wb") as f:
            content = await dci_certificate.read()
            f.write(content)
        dci_certificate_path = f"/certificates/{filename}"

    if govt_id and govt_id.filename:
        file_extension = govt_id.filename.split('.')[-1]
        filename = f"govt_{mobile_number}_{int(time.time())}.{file_extension}"
        file_path = os.path.join("uploads", "govt_ids", filename)
        with open(file_path, "wb") as f:
            content = await govt_id.read()
            f.write(content)
        govt_id_path = f"/govt_ids/{filename}"

    user = AuthService.register_doctor(
        db=db,
        mobile_number=mobile_number,
        full_name=full_name,
        specialization=specialization,
        years_of_experience=years_of_experience,
        dci_registration_number=dci_registration_number,
        qualification_bds=qualification_bds,
        qualification_mds=qualification_mds,
        additional_qualifications=additional_qualifications,
        consultation_fee_online=consultation_fee_online,
        consultation_fee_offline=consultation_fee_offline,
        online_consultation_available=online_consultation_available,
        available_days=available_days,
        booking_limit_per_day=booking_limit_per_day,
        services_offered=services_offered,
        profile_image_path=profile_image_path,
        dci_certificate_path=dci_certificate_path,
        govt_id_path=govt_id_path
    )

    return {
        "message": "Doctor registered successfully. Pending admin approval.",
        "user_id": user.id,
        "mobile_number": mobile_number
    }


@router.get("/profile", response_model=DoctorResponse)
def get_doctor_profile(
    current_user: User = Depends(require_role([UserRole.DOCTOR])),
    db: Session = Depends(get_db)
):
    """Get current doctor's profile"""
    doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor profile not found"
        )
    return doctor


@router.put("/profile", response_model=DoctorResponse)
def update_doctor_profile(
    update_data: DoctorUpdate,
    current_user: User = Depends(require_role([UserRole.DOCTOR])),
    db: Session = Depends(get_db)
):
    """Update doctor profile"""
    doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor profile not found"
        )

    update_dict = update_data.dict(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(doctor, field, value)

    db.commit()
    db.refresh(doctor)
    return doctor


@router.get("/search", response_model=List[DoctorResponse])
def search_doctors(
    specialization: Optional[str] = None,
    name: Optional[str] = None,
    online_available: Optional[bool] = None,
    page: int = 1,
    per_page: int = 20,
    db: Session = Depends(get_db)
):
    """Search doctors by specialization, name, or availability"""
    query = db.query(Doctor).filter(Doctor.is_active == True)

    if specialization:
        query = query.filter(Doctor.specialization.ilike(f"%{specialization}%"))
    if name:
        query = query.filter(Doctor.full_name.ilike(f"%{name}%"))
    if online_available is not None:
        query = query.filter(Doctor.online_consultation_available == online_available)

    offset = (page - 1) * per_page
    doctors = query.offset(offset).limit(per_page).all()
    return doctors


@router.get("/{doctor_id}", response_model=DoctorResponse)
def get_doctor_by_id(
    doctor_id: str,
    db: Session = Depends(get_db)
):
    """Get doctor by ID"""
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found"
        )
    return doctor


@router.get("/availability/{doctor_id}")
def get_doctor_availability(
    doctor_id: str,
    db: Session = Depends(get_db)
):
    """Get doctor availability"""
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found"
        )
    return {
        "available_days": doctor.available_days,
        "booking_limit_per_day": doctor.booking_limit_per_day,
        "online_consultation_available": doctor.online_consultation_available,
        "consultation_fee_online": doctor.consultation_fee_online,
        "consultation_fee_offline": doctor.consultation_fee_offline
    }


@router.post("/upload-profile-image")
async def upload_profile_image(
    file: UploadFile = File(...),
    current_user: User = Depends(require_role([UserRole.DOCTOR])),
    db: Session = Depends(get_db)
):
    """Upload profile image"""
    doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor profile not found")
    file_path = await FileService.save_file(file, "profile_images", f"doctor_{doctor.doctor_id}")
    doctor.profile_image_path = file_path
    db.commit()
    return {"profile_image_path": file_path}
