from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime

class ClinicalProfileBase(BaseModel):
    occupation: Optional[str] = None
    visit_date: Optional[date] = None
    referred_by: Optional[str] = None

class ClinicalProfileCreate(ClinicalProfileBase):
    patient_id: int
    appointment_id: Optional[int] = None
    
    # Chief Complaint
    primary_complaint: Optional[str] = None
    complaint_duration: Optional[str] = None
    complaint_progression: Optional[str] = None
    associated_symptoms: Optional[str] = None
    
    # HPI
    hpi_onset_duration: Optional[str] = None
    hpi_nature_of_pain: Optional[str] = None
    hpi_aggravating_factors: Optional[str] = None
    hpi_relieving_factors: Optional[str] = None
    hpi_medication_taken: Optional[str] = None
    hpi_previous_treatment: Optional[str] = None
    
    # Past Dental History
    last_dental_visit: Optional[str] = None
    past_treatments: Optional[str] = None
    brushing_frequency: Optional[str] = None
    brushing_method: Optional[str] = None
    other_oral_aids: Optional[str] = None
    
    # Medical History
    systemic_diseases: Optional[str] = None
    current_medications: Optional[str] = None
    hospitalization_history: Optional[str] = None
    known_allergies: Optional[str] = None
    smoking_tobacco: Optional[str] = None
    alcohol_use: Optional[str] = None
    pregnancy_lactation: Optional[str] = None
    
    # Family History
    family_medical_conditions: Optional[str] = None
    
    # Personal History
    diet: Optional[str] = None
    sleep_pattern: Optional[str] = None
    stress_anxiety: Optional[str] = None
    oral_habits: Optional[str] = None
    
    # General Examination
    bp: Optional[str] = None
    pulse: Optional[str] = None
    temperature: Optional[str] = None
    oxygen_saturation: Optional[str] = None
    build_nourishment: Optional[str] = None
    pallor_cyanosis: Optional[str] = None
    face_symmetry: Optional[str] = None
    
    # Extraoral Examination
    tmj_movement: Optional[str] = None
    lymph_nodes: Optional[str] = None
    facial_asymmetry: Optional[str] = None
    mouth_opening_mm: Optional[float] = None
    clicking_pain: Optional[str] = None
    
    # Intraoral - Soft Tissues
    soft_tissue_lips: Optional[str] = None
    soft_tissue_buccal_mucosa: Optional[str] = None
    soft_tissue_tongue: Optional[str] = None
    soft_tissue_floor_of_mouth: Optional[str] = None
    soft_tissue_palate: Optional[str] = None
    soft_tissue_gingiva: Optional[str] = None
    oral_hygiene_index: Optional[str] = None
    
    # Intraoral - Teeth
    missing_teeth: Optional[str] = None
    caries: Optional[str] = None
    discoloration: Optional[str] = None
    attrition_abrasion_erosion: Optional[str] = None
    mobility: Optional[str] = None
    malocclusion: Optional[str] = None
    occlusion_status: Optional[str] = None
    
    # Radiographic
    radiographic_type: Optional[str] = None
    radiographic_observations: Optional[str] = None
    
    # Diagnosis
    provisional_diagnosis: Optional[str] = None
    differential_diagnosis: Optional[str] = None
    final_diagnosis: Optional[str] = None
    
    # Treatment Plan
    treatment_phase_1: Optional[str] = None
    treatment_phase_2: Optional[str] = None
    treatment_phase_3: Optional[str] = None
    
    # Consent
    consent_obtained: bool = False

class ClinicalProfileUpdate(ClinicalProfileBase):
    primary_complaint: Optional[str] = None
    complaint_duration: Optional[str] = None
    systemic_diseases: Optional[str] = None
    provisional_diagnosis: Optional[str] = None
    final_diagnosis: Optional[str] = None
    treatment_phase_1: Optional[str] = None
    consent_obtained: Optional[bool] = None
    # Add other fields as needed

class ClinicalProfileResponse(ClinicalProfileBase):
    id: int
    profile_id: str
    patient_id: int
    doctor_id: int
    appointment_id: Optional[int]
    xray_image_path: Optional[str]
    xray_analysis_result: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True
