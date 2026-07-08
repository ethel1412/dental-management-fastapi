from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import status as http_status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date
from app.database import get_db
from app.models.user import User, UserRole
from app.models.appointment import Appointment, AppointmentStatus
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.schemas.appointment import AppointmentCreate, AppointmentUpdate, AppointmentResponse
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/api/appointments", tags=["Appointments"])


@router.post("", response_model=AppointmentResponse)
def create_appointment(
    appointment_data: AppointmentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new appointment"""
    doctor = db.query(Doctor).filter(Doctor.id == appointment_data.doctor_id).first()
    if not doctor:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Doctor not found"
        )

    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    if not patient:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Patient profile not found"
        )

    new_appointment = Appointment(
        patient_id=patient.id,
        doctor_id=appointment_data.doctor_id,
        appointment_date=appointment_data.appointment_date,
        appointment_time=appointment_data.appointment_time,
        consultation_type=appointment_data.consultation_type,
        reason=appointment_data.reason,
        notes=appointment_data.notes,
        status=AppointmentStatus.PENDING
    )

    db.add(new_appointment)
    db.commit()
    db.refresh(new_appointment)

    return new_appointment


def _get_appointments_for_user(
    current_user: User,
    db: Session,
    appointment_status: Optional[AppointmentStatus] = None,
    upcoming: bool = False,
    page: int = 1,
    per_page: int = 10,
):
    """Shared logic for fetching appointments for the current user."""
    query = db.query(Appointment)

    if current_user.role == UserRole.PATIENT:
        patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
        if not patient:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="Patient profile not found"
            )
        query = query.filter(Appointment.patient_id == patient.id)

    elif current_user.role == UserRole.DOCTOR:
        doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
        if not doctor:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="Doctor profile not found"
            )
        query = query.filter(Appointment.doctor_id == doctor.id)

    else:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    if appointment_status:
        query = query.filter(Appointment.status == appointment_status)

    if upcoming:
        query = query.filter(Appointment.appointment_date >= date.today())

    query = query.order_by(Appointment.appointment_date.asc())

    offset = (page - 1) * per_page
    return query.offset(offset).limit(per_page).all()


@router.get("", response_model=List[AppointmentResponse])
def get_my_appointments(
    appointment_status: Optional[AppointmentStatus] = Query(None, alias="status"),
    upcoming: bool = False,
    page: int = 1,
    per_page: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get appointments for current user (GET /api/appointments)"""
    return _get_appointments_for_user(current_user, db, appointment_status, upcoming, page, per_page)


# Named alias that Flutter currently calls: GET /api/appointments/my-appointments
# MUST be declared BEFORE /{appointment_id} to avoid route conflict
@router.get("/my-appointments", response_model=List[AppointmentResponse])
def get_my_appointments_alias(
    appointment_status: Optional[AppointmentStatus] = Query(None, alias="status"),
    upcoming: bool = False,
    page: int = 1,
    per_page: int = 200,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Alias: GET /api/appointments/my-appointments — same as GET /api/appointments"""
    return _get_appointments_for_user(current_user, db, appointment_status, upcoming, page, per_page)


@router.get("/{appointment_id}", response_model=AppointmentResponse)
def get_appointment(
    appointment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific appointment by ID"""
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    return appointment


@router.put("/{appointment_id}", response_model=AppointmentResponse)
def update_appointment(
    appointment_id: str,
    update_data: AppointmentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update appointment status or details"""
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )

    update_dict = update_data.dict(exclude_unset=True)
    for field, value in update_dict.items():
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
    """Cancel an appointment"""
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )

    appointment.status = AppointmentStatus.CANCELLED
    db.commit()
    return {"message": "Appointment cancelled successfully"}
