from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User, UserRole
from app.models.patient import Patient
from app.schemas.patient import PatientCreate, PatientUpdate, PatientResponse
from app.services.auth_service import AuthService
from app.services.file_service import FileService
from app.utils.dependencies import require_role
from app.utils.security import generate_unique_id

router = APIRouter(prefix="/api/patients", tags=["Patients"])

@router.post("/register", response_model=dict)
def register_patient(patient_data: PatientCreate, db: Session = Depends(get_db)):
    """Register a new patient"""
    # Register user first
    user = AuthService.register_user(
        db=db,
        mobile_number=patient_data.mobile_number,
        email=patient_data.email,
        password=patient_data.password,
        role=UserRole.PATIENT
    )
    
    # Generate patient ID
    last_patient = db.query(Patient).order_by(Patient.id.desc()).first()
    patient_id = generate_unique_id("PAT", last_patient.id if last_patient else None)
    
    # Create patient profile
    new_patient = Patient(
        user_id=user.id,
        patient_id=patient_id,
        full_name=patient_data.full_name,
        age=patient_data.age,
        date_of_birth=patient_data.date_of_birth,
        gender=patient_data.gender,
        address=patient_data.address,
        pincode=patient_data.pincode,
        consent_given=patient_data.consent_given
    )
    
    db.add(new_patient)
    db.commit()
    db.refresh(new_patient)
    
    return {
        "message": "Patient registered successfully. Please verify OTP",
        "otp": user.otp,
        "patient_id": new_patient.patient_id,
        "user_id": user.id
    }

@router.get("/profile", response_model=PatientResponse)
def get_patient_profile(current_user: User = Depends(require_role([UserRole.PATIENT]))):
    """Get current patient's profile"""
    patient = current_user.patient_profile
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient profile not found"
        )
    return patient

@router.put("/profile", response_model=PatientResponse)
def update_patient_profile(
    patient_update: PatientUpdate,
    current_user: User = Depends(require_role([UserRole.PATIENT])),
    db: Session = Depends(get_db)
):
    """Update patient profile"""
    patient = current_user.patient_profile
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient profile not found"
        )
    
    update_data = patient_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(patient, field, value)
    
    db.commit()
    db.refresh(patient)
    return patient

@router.post("/upload-profile-image")
async def upload_profile_image(
    file: UploadFile = File(...),
    current_user: User = Depends(require_role([UserRole.PATIENT])),
    db: Session = Depends(get_db)
):
    """Upload patient profile image"""
    patient = current_user.patient_profile
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient profile not found"
        )
    
    file_path = await FileService.save_file(file, "profile_images", f"patient_{patient.patient_id}")
    patient.profile_image_path = file_path
    db.commit()
    
    return {
        "message": "Profile image uploaded successfully",
        "file_path": FileService.get_file_url(file_path)
    }

@router.get("/{patient_id}", response_model=PatientResponse)
def get_patient_by_id(
    patient_id: str,
    current_user: User = Depends(require_role([UserRole.DOCTOR, UserRole.PATIENT])),
    db: Session = Depends(get_db)
):
    """Get patient by ID (for doctors or own profile)"""
    patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )
    
    # If patient role, can only view own profile
    if current_user.role == UserRole.PATIENT:
        if patient.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    
    return patient
