from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date, time
from app.database import get_db
from app.models.user import User, UserRole
from app.models.appointment import Appointment, AppointmentStatus
from app.models.doctor import Doctor
from app.models.clinic import Clinic
from app.schemas.appointment import AppointmentCreate, AppointmentUpdate, AppointmentResponse
from app.utils.dependencies import get_current_user, require_role
from app.utils.security import generate_unique_id

router = APIRouter(prefix="/api/appointments", tags=["Appointments"])

@router.post("/", response_model=AppointmentResponse)
def create_appointment(
    appointment_data: AppointmentCreate,
    current_user: User = Depends(require_role([UserRole.PATIENT])),
    db: Session = Depends(get_db)
):
    """Book a new appointment"""
    patient = current_user.patient_profile
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient profile not found"
        )
    
    # Verify doctor and clinic exist
    doctor = db.query(Doctor).filter(Doctor.id == appointment_data.doctor_id).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found"
        )
    
    clinic = db.query(Clinic).filter(Clinic.id == appointment_data.clinic_id).first()
    if not clinic or clinic.doctor_id != doctor.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clinic not found or doesn't belong to this doctor"
        )
    
    # Check booking limit
    existing_appointments = db.query(Appointment).filter(
        Appointment.doctor_id == doctor.id,
        Appointment.appointment_date == appointment_data.appointment_date,
        Appointment.status.in_([AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED])
    ).count()
    
    if existing_appointments >= doctor.booking_limit_per_day:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Doctor's booking limit reached for this date. Limit: {doctor.booking_limit_per_day}"
        )
    
    # Check for time slot conflicts
    conflict = db.query(Appointment).filter(
        Appointment.doctor_id == doctor.id,
        Appointment.clinic_id == clinic.id,
        Appointment.appointment_date == appointment_data.appointment_date,
        Appointment.appointment_time == appointment_data.appointment_time,
        Appointment.status.in_([AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED])
    ).first()
    
    if conflict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This time slot is already booked"
        )
    
    # Generate appointment ID
    last_appointment = db.query(Appointment).order_by(Appointment.id.desc()).first()
    appointment_id = generate_unique_id("APT", last_appointment.id if last_appointment else None)
    
    # Create appointment
    new_appointment = Appointment(
        appointment_id=appointment_id,
        patient_id=patient.id,
        doctor_id=doctor.id,
        clinic_id=clinic.id,
        appointment_date=appointment_data.appointment_date,
        appointment_time=appointment_data.appointment_time,
        duration_minutes=appointment_data.duration_minutes,
        reason=appointment_data.reason,
        status=AppointmentStatus.SCHEDULED
    )
    
    db.add(new_appointment)
    db.commit()
    db.refresh(new_appointment)
    
    return new_appointment

@router.get("/my-appointments", response_model=List[AppointmentResponse])
def get_my_appointments(
    status: Optional[AppointmentStatus] = None,
    upcoming: bool = True,
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get appointments for current user (patient or doctor)"""
    query = db.query(Appointment)
    
    if current_user.role == UserRole.PATIENT:
        patient = current_user.patient_profile
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient profile not found"
            )
        query = query.filter(Appointment.patient_id == patient.id)
    
    elif current_user.role == UserRole.DOCTOR:
        doctor = current_user.doctor_profile
        if not doctor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Doctor profile not found"
            )
        query = query.filter(Appointment.doctor_id == doctor.id)
    
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    if status:
        query = query.filter(Appointment.status == status)
    
    if upcoming:
        today = date.today()
        query = query.filter(Appointment.appointment_date >= today)
    
    query = query.order_by(Appointment.appointment_date.desc(), Appointment.appointment_time.desc())
    
    offset = (page - 1) * per_page
    appointments = query.offset(offset).limit(per_page).all()
    
    return appointments

@router.get("/{appointment_id}", response_model=AppointmentResponse)
def get_appointment(
    appointment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get appointment by ID"""
    appointment = db.query(Appointment).filter(Appointment.appointment_id == appointment_id).first()
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    
    # Check access
    if current_user.role == UserRole.PATIENT:
        if appointment.patient.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    elif current_user.role == UserRole.DOCTOR:
        if appointment.doctor.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    
    return appointment

@router.put("/{appointment_id}", response_model=AppointmentResponse)
def update_appointment(
    appointment_id: str,
    appointment_update: AppointmentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update appointment"""
    appointment = db.query(Appointment).filter(Appointment.appointment_id == appointment_id).first()
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    
    # Check access
    if current_user.role == UserRole.PATIENT:
        if appointment.patient.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    elif current_user.role == UserRole.DOCTOR:
        if appointment.doctor.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    
    update_data = appointment_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(appointment, field, value)
    
    db.commit()
    db.refresh(appointment)
    return appointment

@router.delete("/{appointment_id}")
def cancel_appointment(
    appointment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancel appointment"""
    appointment = db.query(Appointment).filter(Appointment.appointment_id == appointment_id).first()
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    
    # Check access
    if current_user.role == UserRole.PATIENT:
        if appointment.patient.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    elif current_user.role == UserRole.DOCTOR:
        if appointment.doctor.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    
    appointment.status = AppointmentStatus.CANCELLED
    db.commit()
    
    return {"message": "Appointment cancelled successfully"}

@router.get("/doctor/{doctor_id}/availability")
def check_doctor_availability(
    doctor_id: str,
    date: str,
    db: Session = Depends(get_db)
):
    """Check doctor's availability for a specific date"""
    doctor = db.query(Doctor).filter(Doctor.doctor_id == doctor_id).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found"
        )
    
    check_date = datetime.strptime(date, "%Y-%m-%d").date()
    
    # Get existing appointments
    existing_appointments = db.query(Appointment).filter(
        Appointment.doctor_id == doctor.id,
        Appointment.appointment_date == check_date,
        Appointment.status.in_([AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED])
    ).all()
    
    booked_slots = len(existing_appointments)
    remaining_slots = doctor.booking_limit_per_day - booked_slots
    
    # Get booked times
    booked_times = [apt.appointment_time.strftime("%H:%M") for apt in existing_appointments]
    
    return {
        "doctor_id": doctor.doctor_id,
        "date": date,
        "booking_limit": doctor.booking_limit_per_day,
        "booked_slots": booked_slots,
        "remaining_slots": remaining_slots,
        "is_available": remaining_slots > 0,
        "booked_times": booked_times
    }
