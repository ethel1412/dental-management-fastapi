from sqlalchemy.orm import Session
from app.models.doctor import Doctor
from app.models.user import User
from app.utils.security import generate_unique_id
from fastapi import HTTPException

class DoctorService:
    
    @staticmethod
    def create_doctor(
        db: Session,
        mobile_number: str,
        full_name: str,
        specialization: str,
        years_of_experience: int,
        dci_registration_number: str,
        qualification_bds: str,
        consultation_fee_offline: float,
        booking_limit_per_day: int,
        qualification_mds: str = None,
        additional_qualifications: str = None,
        consultation_fee_online: float = None,
        dci_certificate_path: str = None,
        profile_image_path: str = None
    ):
        """Create a new doctor profile"""
        
        # Check if user exists with this mobile number
        user = db.query(User).filter(User.mobile_number == mobile_number).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if user.role != "doctor":
            raise HTTPException(status_code=400, detail="User is not registered as a doctor")
        
        # Check if doctor profile already exists
        existing_doctor = db.query(Doctor).filter(Doctor.user_id == user.id).first()
        if existing_doctor:
            raise HTTPException(status_code=400, detail="Doctor profile already exists")
        
        # Generate unique doctor ID
        doctor_id = generate_unique_id(prefix="DOC", length=8)
        
        # Create doctor
        new_doctor = Doctor(
            doctor_id=doctor_id,
            user_id=user.id,
            full_name=full_name,
            specialization=specialization,
            years_of_experience=years_of_experience,
            dci_registration_number=dci_registration_number,
            qualification_bds=qualification_bds,
            qualification_mds=qualification_mds,
            other_qualifications=additional_qualifications,
            dci_certificate_path=dci_certificate_path,
            profile_image_path=profile_image_path,
            consultation_fee_offline=consultation_fee_offline,
            consultation_fee_online=consultation_fee_online,
            booking_limit_per_day=booking_limit_per_day,
            is_active=True
        )
        
        db.add(new_doctor)
        db.commit()
        db.refresh(new_doctor)
        
        return new_doctor
    
    @staticmethod
    def get_doctor_by_user_id(db: Session, user_id: int):
        """Get doctor by user ID"""
        return db.query(Doctor).filter(Doctor.user_id == user_id).first()
    
    @staticmethod
    def get_doctor_by_id(db: Session, doctor_id: int):
        """Get doctor by doctor ID"""
        return db.query(Doctor).filter(Doctor.id == doctor_id).first()
    
    @staticmethod
    def get_all_doctors(db: Session, skip: int = 0, limit: int = 100):
        """Get all doctors"""
        return db.query(Doctor).filter(Doctor.is_active == True).offset(skip).limit(limit).all()
    
    @staticmethod
    def search_doctors(
        db: Session,
        specialization: str = None,
        city: str = None,
        name: str = None
    ):
        """Search doctors by filters"""
        query = db.query(Doctor).filter(Doctor.is_active == True)
        
        if specialization:
            query = query.filter(Doctor.specialization.ilike(f"%{specialization}%"))
        
        if name:
            query = query.filter(Doctor.full_name.ilike(f"%{name}%"))
        
        return query.all()
    
    @staticmethod
    def update_doctor(db: Session, doctor_id: int, update_data: dict):
        """Update doctor profile"""
        doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
        
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor not found")
        
        for key, value in update_data.items():
            if hasattr(doctor, key) and value is not None:
                setattr(doctor, key, value)
        
        db.commit()
        db.refresh(doctor)
        
        return doctor
