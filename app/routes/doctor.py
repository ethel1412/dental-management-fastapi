from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models.user import User, UserRole
from app.models.doctor import Doctor
from app.schemas.doctor import DoctorCreate, DoctorUpdate, DoctorResponse, DoctorSearchFilters
from app.services.auth_service import AuthService
from app.services.file_service import FileService
from app.utils.dependencies import get_current_user, require_role
from app.utils.security import generate_unique_id

router = APIRouter(prefix="/api/doctors", tags=["Doctors"])

@router.post("/register", response_model=dict)
def register_doctor(doctor_data: DoctorCreate, db: Session = Depends(get_db)):
    """Register a new doctor"""
    # Register user first
    user = AuthService.register_user(
        db=db,
        mobile_number=doctor_data.mobile_number,
        email=doctor_data.email,
        password=doctor_data.password,
        role=UserRole.DOCTOR
    )
    
    # Check if DCI number exists
    existing_doctor = db.query(Doctor).filter(
        Doctor.dci_registration_number == doctor_data.dci_registration_number
    ).first()
    
    if existing_doctor:
        db.delete(user)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="DCI registration number already exists"
        )
    
    # Generate doctor ID
    last_doctor = db.query(Doctor).order_by(Doctor.id.desc()).first()
    doctor_id = generate_unique_id("DOC", last_doctor.id if last_doctor else None)
    
    # Create doctor profile
    new_doctor = Doctor(
        user_id=user.id,
        doctor_id=doctor_id,
        full_name=doctor_data.full_name,
        specialization=doctor_data.specialization,
        years_of_experience=doctor_data.years_of_experience,
        dci_registration_number=doctor_data.dci_registration_number,
        qualification_bds=doctor_data.qualification_bds,
        qualification_mds=doctor_data.qualification_mds,
        qualification_fellowship=doctor_data.qualification_fellowship,
        other_qualifications=doctor_data.other_qualifications,
        consultation_fee_online=doctor_data.consultation_fee_online,
        consultation_fee_offline=doctor_data.consultation_fee_offline,
        online_consultation_available=doctor_data.online_consultation_available,
        available_days=doctor_data.available_days,
        booking_limit_per_day=doctor_data.booking_limit_per_day,
        services_offered=doctor_data.services_offered,
        account_holder_name=doctor_data.account_holder_name,
        account_number=doctor_data.account_number,
        ifsc_code=doctor_data.ifsc_code,
        upi_id=doctor_data.upi_id
    )
    
    db.add(new_doctor)
    db.commit()
    db.refresh(new_doctor)
    
    return {
        "message": "Doctor registered successfully. Please verify OTP",
        "otp": user.otp,
        "doctor_id": new_doctor.doctor_id,
        "user_id": user.id
    }

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
    
    # Update fields
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor profile not found"
        )
    
    # Save file
    file_path = await FileService.save_file(file, "certificates", f"dci_{doctor.doctor_id}")
    
    # Update doctor profile
    doctor.dci_certificate_path = file_path
    db.commit()
    
    return {
        "message": "DCI certificate uploaded successfully",
        "file_path": FileService.get_file_url(file_path)
    }

@router.post("/upload-govt-id")
async def upload_govt_id(
    file: UploadFile = File(...),
    current_user: User = Depends(require_role([UserRole.DOCTOR])),
    db: Session = Depends(get_db)
):
    """Upload government ID"""
    doctor = current_user.doctor_profile
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor profile not found"
        )
    
    file_path = await FileService.save_file(file, "certificates", f"govt_id_{doctor.doctor_id}")
    doctor.govt_id_path = file_path
    db.commit()
    
    return {
        "message": "Government ID uploaded successfully",
        "file_path": FileService.get_file_url(file_path)
    }

@router.post("/upload-profile-image")
async def upload_profile_image(
    file: UploadFile = File(...),
    current_user: User = Depends(require_role([UserRole.DOCTOR])),
    db: Session = Depends(get_db)
):
    """Upload profile image"""
    doctor = current_user.doctor_profile
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor profile not found"
        )
    
    file_path = await FileService.save_file(file, "profile_images", f"doctor_{doctor.doctor_id}")
    doctor.profile_image_path = file_path
    db.commit()
    
    return {
        "message": "Profile image uploaded successfully",
        "file_path": FileService.get_file_url(file_path)
    }

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
    
    # If city or pincode filter, join with clinics
    if city or pincode:
        from app.models.clinic import Clinic
        query = query.join(Doctor.clinics)
        if city:
            query = query.filter(Clinic.city.ilike(f"%{city}%"))
        if pincode:
            query = query.filter(Clinic.pincode == pincode)
    
    # Pagination
    offset = (page - 1) * per_page
    doctors = query.offset(offset).limit(per_page).all()
    
    return doctors

@router.get("/{doctor_id}", response_model=DoctorResponse)
def get_doctor_by_id(doctor_id: str, db: Session = Depends(get_db)):
    """Get doctor by ID"""
    doctor = db.query(Doctor).filter(Doctor.doctor_id == doctor_id).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found"
        )
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
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    query = db.query(Appointment).filter(Appointment.doctor_id == doctor.id)
    
    if date:
        date_obj = datetime.strptime(date, "%Y-%m-%d").date()
        query = query.filter(Appointment.appointment_date == date_obj)
    
    appointments = query.all()
    
    # Check booking limit
    remaining_slots = doctor.booking_limit_per_day - len(appointments) if date else None
    
    return {
        "appointments": appointments,
        "total": len(appointments),
        "booking_limit": doctor.booking_limit_per_day,
        "remaining_slots": remaining_slots
    }
