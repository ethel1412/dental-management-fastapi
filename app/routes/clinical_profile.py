from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.user import User, UserRole
from app.models.clinical_profile import ClinicalProfile
from app.models.appointment import Appointment
from app.schemas.clinical_profile import ClinicalProfileCreate, ClinicalProfileUpdate, ClinicalProfileResponse
from app.services.file_service import FileService
from app.services.ml_service import ml_service
from app.utils.dependencies import require_role
from app.utils.security import generate_unique_id
import json

router = APIRouter(prefix="/api/clinical-profiles", tags=["Clinical Profiles"])

@router.post("/", response_model=ClinicalProfileResponse)
def create_clinical_profile(
    profile_data: ClinicalProfileCreate,
    current_user: User = Depends(require_role([UserRole.DOCTOR])),
    db: Session = Depends(get_db)
):
    """Create clinical profile for a patient (by doctor)"""
    doctor = current_user.doctor_profile
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor profile not found"
        )
    
    # Verify appointment if provided
    if profile_data.appointment_id:
        appointment = db.query(Appointment).filter(
            Appointment.id == profile_data.appointment_id,
            Appointment.doctor_id == doctor.id
        ).first()
        if not appointment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Appointment not found or access denied"
            )
    
    # Generate profile ID
    last_profile = db.query(ClinicalProfile).order_by(ClinicalProfile.id.desc()).first()
    profile_id = generate_unique_id("CP", last_profile.id if last_profile else None)
    
    # Create clinical profile
    new_profile = ClinicalProfile(
        profile_id=profile_id,
        patient_id=profile_data.patient_id,
        doctor_id=doctor.id,
        appointment_id=profile_data.appointment_id,
        occupation=profile_data.occupation,
        visit_date=profile_data.visit_date,
        referred_by=profile_data.referred_by,
        primary_complaint=profile_data.primary_complaint,
        complaint_duration=profile_data.complaint_duration,
        complaint_progression=profile_data.complaint_progression,
        associated_symptoms=profile_data.associated_symptoms,
        hpi_onset_duration=profile_data.hpi_onset_duration,
        hpi_nature_of_pain=profile_data.hpi_nature_of_pain,
        hpi_aggravating_factors=profile_data.hpi_aggravating_factors,
        hpi_relieving_factors=profile_data.hpi_relieving_factors,
        hpi_medication_taken=profile_data.hpi_medication_taken,
        hpi_previous_treatment=profile_data.hpi_previous_treatment,
        last_dental_visit=profile_data.last_dental_visit,
        past_treatments=profile_data.past_treatments,
        brushing_frequency=profile_data.brushing_frequency,
        brushing_method=profile_data.brushing_method,
        other_oral_aids=profile_data.other_oral_aids,
        systemic_diseases=profile_data.systemic_diseases,
        current_medications=profile_data.current_medications,
        hospitalization_history=profile_data.hospitalization_history,
        known_allergies=profile_data.known_allergies,
        smoking_tobacco=profile_data.smoking_tobacco,
        alcohol_use=profile_data.alcohol_use,
        pregnancy_lactation=profile_data.pregnancy_lactation,
        family_medical_conditions=profile_data.family_medical_conditions,
        diet=profile_data.diet,
        sleep_pattern=profile_data.sleep_pattern,
        stress_anxiety=profile_data.stress_anxiety,
        oral_habits=profile_data.oral_habits,
        bp=profile_data.bp,
        pulse=profile_data.pulse,
        temperature=profile_data.temperature,
        oxygen_saturation=profile_data.oxygen_saturation,
        build_nourishment=profile_data.build_nourishment,
        pallor_cyanosis=profile_data.pallor_cyanosis,
        face_symmetry=profile_data.face_symmetry,
        tmj_movement=profile_data.tmj_movement,
        lymph_nodes=profile_data.lymph_nodes,
        facial_asymmetry=profile_data.facial_asymmetry,
        mouth_opening_mm=profile_data.mouth_opening_mm,
        clicking_pain=profile_data.clicking_pain,
        soft_tissue_lips=profile_data.soft_tissue_lips,
        soft_tissue_buccal_mucosa=profile_data.soft_tissue_buccal_mucosa,
        soft_tissue_tongue=profile_data.soft_tissue_tongue,
        soft_tissue_floor_of_mouth=profile_data.soft_tissue_floor_of_mouth,
        soft_tissue_palate=profile_data.soft_tissue_palate,
        soft_tissue_gingiva=profile_data.soft_tissue_gingiva,
        oral_hygiene_index=profile_data.oral_hygiene_index,
        missing_teeth=profile_data.missing_teeth,
        caries=profile_data.caries,
        discoloration=profile_data.discoloration,
        attrition_abrasion_erosion=profile_data.attrition_abrasion_erosion,
        mobility=profile_data.mobility,
        malocclusion=profile_data.malocclusion,
        occlusion_status=profile_data.occlusion_status,
        radiographic_type=profile_data.radiographic_type,
        radiographic_observations=profile_data.radiographic_observations,
        provisional_diagnosis=profile_data.provisional_diagnosis,
        differential_diagnosis=profile_data.differential_diagnosis,
        final_diagnosis=profile_data.final_diagnosis,
        treatment_phase_1=profile_data.treatment_phase_1,
        treatment_phase_2=profile_data.treatment_phase_2,
        treatment_phase_3=profile_data.treatment_phase_3,
        consent_obtained=profile_data.consent_obtained
    )
    
    db.add(new_profile)
    db.commit()
    db.refresh(new_profile)
    
    return new_profile

@router.get("/patient/{patient_id}", response_model=List[ClinicalProfileResponse])
def get_patient_clinical_profiles(
    patient_id: int,
    current_user: User = Depends(require_role([UserRole.DOCTOR, UserRole.PATIENT])),
    db: Session = Depends(get_db)
):
    """Get all clinical profiles for a patient"""
    # Check access
    if current_user.role == UserRole.PATIENT:
        patient = current_user.patient_profile
        if not patient or patient.id != patient_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    
    profiles = db.query(ClinicalProfile).filter(
        ClinicalProfile.patient_id == patient_id
    ).order_by(ClinicalProfile.created_at.desc()).all()
    
    return profiles

@router.get("/{profile_id}", response_model=ClinicalProfileResponse)
def get_clinical_profile(
    profile_id: str,
    current_user: User = Depends(require_role([UserRole.DOCTOR, UserRole.PATIENT])),
    db: Session = Depends(get_db)
):
    """Get clinical profile by ID"""
    profile = db.query(ClinicalProfile).filter(ClinicalProfile.profile_id == profile_id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clinical profile not found"
        )
    
    # Check access
    if current_user.role == UserRole.PATIENT:
        patient = current_user.patient_profile
        if not patient or profile.patient_id != patient.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    elif current_user.role == UserRole.DOCTOR:
        doctor = current_user.doctor_profile
        if not doctor or profile.doctor_id != doctor.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    
    return profile

@router.put("/{profile_id}", response_model=ClinicalProfileResponse)
def update_clinical_profile(
    profile_id: str,
    profile_update: ClinicalProfileUpdate,
    current_user: User = Depends(require_role([UserRole.DOCTOR])),
    db: Session = Depends(get_db)
):
    """Update clinical profile"""
    doctor = current_user.doctor_profile
    profile = db.query(ClinicalProfile).filter(ClinicalProfile.profile_id == profile_id).first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clinical profile not found"
        )
    
    if profile.doctor_id != doctor.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    update_data = profile_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)
    
    db.commit()
    db.refresh(profile)
    return profile

@router.post("/{profile_id}/upload-xray")
async def upload_xray(
    profile_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(require_role([UserRole.DOCTOR])),
    db: Session = Depends(get_db)
):
    """Upload X-ray image for clinical profile"""
    doctor = current_user.doctor_profile
    profile = db.query(ClinicalProfile).filter(ClinicalProfile.profile_id == profile_id).first()
    
    if not profile or profile.doctor_id != doctor.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clinical profile not found"
        )
    
    # Save X-ray image
    file_path = await FileService.save_file(file, "xrays", f"xray_{profile_id}")
    profile.xray_image_path = file_path
    db.commit()
    
    return {
        "message": "X-ray uploaded successfully",
        "file_path": FileService.get_file_url(file_path),
        "profile_id": profile_id
    }

@router.post("/{profile_id}/analyze-xray")
def analyze_xray(
    profile_id: str,
    current_user: User = Depends(require_role([UserRole.DOCTOR])),
    db: Session = Depends(get_db)
):
    """Analyze X-ray using ML model"""
    doctor = current_user.doctor_profile
    profile = db.query(ClinicalProfile).filter(ClinicalProfile.profile_id == profile_id).first()
    
    if not profile or profile.doctor_id != doctor.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clinical profile not found"
        )
    
    if not profile.xray_image_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No X-ray image uploaded for this profile"
        )
    
    # Run ML analysis
    analysis_result = ml_service.analyze_xray(profile.xray_image_path)
    
    # Save result to profile
    profile.xray_analysis_result = json.dumps(analysis_result)
    db.commit()
    
    return {
        "message": "X-ray analysis completed",
        "result": analysis_result
    }
