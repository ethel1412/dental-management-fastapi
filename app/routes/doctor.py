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
    consultation_fee_offline: float = Form(...),
    consultation_fee_online: float = Form(None),
    booking_limit_per_day: int = Form(...),
    dci_certificate: UploadFile = File(None),
    profile_image: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    """Register a new doctor with form data"""
    try:
        print("=== Doctor Registration Started ===")
        
        # Handle file uploads
        dci_certificate_path = None
        profile_image_path = None
        
        if dci_certificate and dci_certificate.filename:
            file_extension = dci_certificate.filename.split('.')[-1]
            filename = f"dci_{mobile_number}_{int(time.time())}.{file_extension}"
            file_path = os.path.join("uploads", "certificates", filename)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, "wb") as buffer:
                content = await dci_certificate.read()
                buffer.write(content)
            dci_certificate_path = f"/certificates/{filename}"
        
        if profile_image and profile_image.filename:
            file_extension = profile_image.filename.split('.')[-1]
            filename = f"profile_{mobile_number}_{int(time.time())}.{file_extension}"
            file_path = os.path.join("uploads", "profiles", filename)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, "wb") as buffer:
                content = await profile_image.read()
                buffer.write(content)
            profile_image_path = f"/profiles/{filename}"
        
        # Create doctor using service
        new_doctor = DoctorService.create_doctor(
            db=db,
            mobile_number=mobile_number,
            full_name=full_name,
            specialization=specialization,
            years_of_experience=years_of_experience,
            dci_registration_number=dci_registration_number,
            qualification_bds=qualification_bds,
            qualification_mds=qualification_mds,
            additional_qualifications=additional_qualifications,
            consultation_fee_offline=consultation_fee_offline,
            consultation_fee_online=consultation_fee_online,
            booking_limit_per_day=booking_limit_per_day,
            dci_certificate_path=dci_certificate_path,
            profile_image_path=profile_image_path
        )
        
        return {
            "message": "Doctor registered successfully", 
            "doctor": new_doctor.to_dict()
        }
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/profile", response_model=DoctorResponse)
def get_doctor_profile(current_user: User = Depends(require_role([UserRole.DOCTOR]))):
    """Get current doctor's profile"""
    doctor = current_user.doctor_profile
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor profile not found"
        )
    return doctor


@router.put("/profile", response_model=DoctorResponse)
def update_doctor_profile(
    doctor_update: DoctorUpdate,
    current_user: User = Depends(require_role([UserRole.DOCTOR])),
    db: Session = Depends(get_db)
):
    """Update doctor profile"""
    doctor = current_user.doctor_profile
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor profile not found"
        )
    
    update_data = doctor_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(doctor, field, value)
    
    db.commit()
    db.refresh(doctor)
    return doctor


@router.post("/upload-dci-certificate")
async def upload_dci_certificate(
    file: UploadFile = File(...),
    current_user: User = Depends(require_role([UserRole.DOCTOR])),
    db: Session = Depends(get_db)
):
    """Upload DCI certificate"""
    doctor = current_user.doctor_profile
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor profile not found")
    
    file_path = await FileService.save_file(file, "certificates", f"dci_{doctor.doctor_id}")
    doctor.dci_certificate_path = file_path
    db.commit()
    
    return {"message": "DCI certificate uploaded successfully", "file_path": FileService.get_file_url(file_path)}


@router.post("/upload-govt-id")
async def upload_govt_id(
    file: UploadFile = File(...),
    current_user: User = Depends(require_role([UserRole.DOCTOR])),
    db: Session = Depends(get_db)
):
    """Upload government ID"""
    doctor = current_user.doctor_profile
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor profile not found")
    
    file_path = await FileService.save_file(file, "certificates", f"govt_id_{doctor.doctor_id}")
    doctor.govt_id_path = file_path
    db.commit()
    
    return {"message": "Government ID uploaded successfully", "file_path": FileService.get_file_url(file_path)}


@router.post("/upload-profile-image")
async def upload_profile_image(
    file: UploadFile = File(...),
    current_user: User = Depends(require_role([UserRole.DOCTOR])),
    db: Session = Depends(get_db)
):
    """Upload profile image"""
    doctor = current_user.doctor_profile
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor profile not found")
    
    file_path = await FileService.save_file(file, "profile_images", f"doctor_{doctor.doctor_id}")
    doctor.profile_image_path = file_path
    db.commit()
    
    return {"message": "Profile image uploaded successfully", "file_path": FileService.get_file_url(file_path)}


@router.get("/search", response_model=List[DoctorResponse])
def search_doctors(
    specialization: Optional[str] = None,
    city: Optional[str] = None,
    pincode: Optional[str] = None,
    online_consultation: Optional[bool] = None,
    max_fee: Optional[float] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Search doctors with filters"""
    query = db.query(Doctor).filter(Doctor.is_active == True)
    
    if specialization:
        query = query.filter(Doctor.specialization.ilike(f"%{specialization}%"))
    if online_consultation is not None:
        query = query.filter(Doctor.online_consultation_available == online_consultation)
    if max_fee:
        query = query.filter(Doctor.consultation_fee_offline <= max_fee)
    
    if city or pincode:
        from app.models.clinic import Clinic
        query = query.join(Doctor.clinics)
        if city:
            query = query.filter(Clinic.city.ilike(f"%{city}%"))
        if pincode:
            query = query.filter(Clinic.pincode == pincode)
    
    offset = (page - 1) * per_page
    doctors = query.offset(offset).limit(per_page).all()
    
    return doctors


@router.get("/{doctor_id}", response_model=DoctorResponse)
def get_doctor_by_id(doctor_id: str, db: Session = Depends(get_db)):
    """Get doctor by ID"""
    doctor = db.query(Doctor).filter(Doctor.doctor_id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")
    return doctor


@router.get("/{doctor_id}/appointments", response_model=dict)
def get_doctor_appointments(
    doctor_id: str,
    date: Optional[str] = None,
    current_user: User = Depends(require_role([UserRole.DOCTOR])),
    db: Session = Depends(get_db)
):
    """Get doctor's appointments"""
    from app.models.appointment import Appointment
    from datetime import datetime
    
    doctor = current_user.doctor_profile
    if doctor.doctor_id != doctor_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    query = db.query(Appointment).filter(Appointment.doctor_id == doctor.id)
    
    if date:
        date_obj = datetime.strptime(date, "%Y-%m-%d").date()
        query = query.filter(Appointment.appointment_date == date_obj)
    
    appointments = query.all()
    remaining_slots = doctor.booking_limit_per_day - len(appointments) if date else None
    
    return {
        "appointments": appointments,
        "total": len(appointments),
        "booking_limit": doctor.booking_limit_per_day,
        "remaining_slots": remaining_slots
    }
