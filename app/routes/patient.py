from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
import os
import time
from app.database import get_db
from app.models.user import User, UserRole
from app.models.patient import Patient
from app.schemas.patient import PatientUpdate, PatientResponse
from app.services.auth_service import AuthService
from app.services.file_service import FileService
from app.utils.dependencies import require_role
from app.utils.security import generate_unique_id


router = APIRouter(prefix="/api/patients", tags=["Patients"])


@router.post("/register", response_model=dict)
async def register_patient(
    mobile_number: str = Form(...),
    full_name: str = Form(...),
    age: int = Form(...),
    gender: str = Form(...),
    email: str = Form(None),
    address: str = Form(None),
    consent_given: bool = Form(True),
    profile_image: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    """Register a new patient with form data"""
    try:
        print("=== Patient Registration Started ===")
        print(f"Mobile: {mobile_number}")
        print(f"Name: {full_name}")
        
        # Check if user exists with this mobile number
        user = db.query(User).filter(User.mobile_number == mobile_number).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found. Please register first.")
        
        if user.role != "patient":
            raise HTTPException(status_code=400, detail="User is not registered as a patient")
        
        # Check if patient profile already exists
        existing_patient = db.query(Patient).filter(Patient.user_id == user.id).first()
        if existing_patient:
            raise HTTPException(status_code=400, detail="Patient profile already exists")
        
        # Handle profile image upload
        profile_image_path = None
        if profile_image and profile_image.filename:
            file_extension = profile_image.filename.split('.')[-1]
            filename = f"patient_{mobile_number}_{int(time.time())}.{file_extension}"
            file_path = os.path.join("uploads", "profiles", filename)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, "wb") as buffer:
                content = await profile_image.read()
                buffer.write(content)
            
            profile_image_path = f"/profiles/{filename}"
        
        # Generate patient ID
        patient_id = generate_unique_id(prefix="PAT", length=8)
        
        # Create patient profile
        new_patient = Patient(
            user_id=user.id,
            patient_id=patient_id,
            full_name=full_name,
            age=age,
            gender=gender,
            address=address,
            consent_given=consent_given,
            profile_image_path=profile_image_path,
            is_active=True
        )
        
        db.add(new_patient)
        db.commit()
        db.refresh(new_patient)
        
        print("Patient created successfully!")
        
        return {
            "message": "Patient registered successfully",
            "patient": new_patient.to_dict()
        }
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/profile", response_model=PatientResponse)
def get_patient_profile(
    current_user: User = Depends(require_role([UserRole.PATIENT])),
    db: Session = Depends(get_db)
):
    """Get current patient's profile"""
    # Query directly — avoids the backref list vs scalar ambiguity
    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
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
    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
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
    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
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


@router.get("/search", response_model=list[PatientResponse])
def search_patients(
    q: str = "",
    current_user: User = Depends(require_role([UserRole.DOCTOR])),
    db: Session = Depends(get_db)
):
    """Search patients by name or patient_id (doctor only)"""
    query = db.query(Patient)
    if q:
        query = query.filter(
            (Patient.full_name.ilike(f"%{q}%")) |
            (Patient.patient_id.ilike(f"%{q}%"))
        )
    return query.limit(50).all()


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
