from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import time
from app.database import get_db
from app.models.user import User, UserRole
from app.models.lab import Lab, LabType
from app.schemas.lab import LabUpdate, LabResponse
from app.services.auth_service import AuthService
from app.services.file_service import FileService
from app.utils.dependencies import get_current_user, require_role
from app.utils.security import generate_unique_id


router = APIRouter(prefix="/api/labs", tags=["Labs"])


@router.post("/register", response_model=dict)
async def register_lab(
    mobile_number: str = Form(...),
    lab_name: str = Form(...),
    owner_name: str = Form(...),
    state: str = Form(...),
    pincode: str = Form(...),
    email: str = Form(None),
    address: str = Form(...),
    city: str = Form(None),
    pickup_available: bool = Form(True),
    delivery_available: bool = Form(True),
    free_delivery: bool = Form(False),
    license_certificate: UploadFile = File(None),
    lab_image: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    """Register a new lab with form data"""
    try:
        print("=== Lab Registration Started ===")
        print(f"Mobile: {mobile_number}")
        print(f"Lab Name: {lab_name}")
        
        # Check if user exists
        user = db.query(User).filter(User.mobile_number == mobile_number).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found. Please register first.")
        
        if user.role != "lab":
            raise HTTPException(status_code=400, detail="User is not registered as a lab")
        
        # Check if lab profile already exists
        existing_lab = db.query(Lab).filter(Lab.user_id == user.id).first()
        if existing_lab:
            raise HTTPException(status_code=400, detail="Lab profile already exists")
        
        # Handle file uploads
        registration_certificate_path = None
        lab_image_path = None
        
        if license_certificate and license_certificate.filename:
            file_extension = license_certificate.filename.split('.')[-1]
            filename = f"license_{mobile_number}_{int(time.time())}.{file_extension}"
            file_path = os.path.join("uploads", "certificates", filename)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, "wb") as buffer:
                content = await license_certificate.read()
                buffer.write(content)
            
            registration_certificate_path = f"/certificates/{filename}"
        
        if lab_image and lab_image.filename:
            file_extension = lab_image.filename.split('.')[-1]
            filename = f"lab_{mobile_number}_{int(time.time())}.{file_extension}"
            file_path = os.path.join("uploads", "profiles", filename)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, "wb") as buffer:
                content = await lab_image.read()
                buffer.write(content)
            
            lab_image_path = f"/profiles/{filename}"
        
        # Generate lab ID
        lab_id = generate_unique_id(prefix="LAB", length=8)
        
        # Generate temporary license number (you can customize this)
        license_number = f"LIC{mobile_number[-6:]}{int(time.time())}"
        
        # Create lab profile
        new_lab = Lab(
            user_id=user.id,
            lab_id=lab_id,
            lab_name=lab_name,
            lab_type=LabType.DENTAL,  # Default to dental
            owner_name=owner_name,
            lab_address=address,
            city=city,
            state=state,
            pincode=pincode,
            license_number=license_number,
            pickup_available=pickup_available,
            delivery_available=delivery_available,
            free_delivery=free_delivery,
            registration_certificate_path=registration_certificate_path,
            lab_image_path=lab_image_path,
            is_active=True
        )
        
        db.add(new_lab)
        db.commit()
        db.refresh(new_lab)
        
        print("Lab created successfully!")
        
        return {
            "message": "Lab registered successfully",
            "lab": new_lab.to_dict()
        }
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))


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
