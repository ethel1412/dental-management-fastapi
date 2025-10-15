from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, Text, ForeignKey, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class ClinicalProfile(Base):
    __tablename__ = "clinical_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(String(20), unique=True, nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    appointment_id = Column(Integer, ForeignKey("appointments.id"))
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    
    # Patient Details
    occupation = Column(String(100))
    visit_date = Column(Date)
    referred_by = Column(String(100))
    
    # Chief Complaint
    primary_complaint = Column(Text)
    complaint_duration = Column(String(100))
    complaint_progression = Column(String(50))  # gradual, sudden, intermittent, continuous
    associated_symptoms = Column(Text)
    
    # History of Present Illness
    hpi_onset_duration = Column(Text)
    hpi_nature_of_pain = Column(String(100))  # sharp, dull, throbbing, continuous, intermittent
    hpi_aggravating_factors = Column(Text)
    hpi_relieving_factors = Column(Text)
    hpi_medication_taken = Column(Text)
    hpi_previous_treatment = Column(Text)
    
    # Past Dental History
    last_dental_visit = Column(String(100))
    past_treatments = Column(Text)  # JSON array
    brushing_frequency = Column(String(20))
    brushing_method = Column(String(20))
    other_oral_aids = Column(Text)  # JSON array
    
    # Medical History
    systemic_diseases = Column(Text)  # JSON array
    current_medications = Column(Text)
    hospitalization_history = Column(Text)
    known_allergies = Column(Text)
    smoking_tobacco = Column(String(50))
    alcohol_use = Column(String(50))
    pregnancy_lactation = Column(String(50))
    
    # Family History
    family_medical_conditions = Column(Text)  # JSON array
    
    # Personal History
    diet = Column(String(50))
    sleep_pattern = Column(String(50))
    stress_anxiety = Column(String(50))
    oral_habits = Column(Text)  # JSON array
    
    # General Examination
    bp = Column(String(20))
    pulse = Column(String(20))
    temperature = Column(String(20))
    oxygen_saturation = Column(String(20))
    build_nourishment = Column(String(50))
    pallor_cyanosis = Column(Text)
    face_symmetry = Column(Text)
    
    # Extraoral Examination
    tmj_movement = Column(Text)
    lymph_nodes = Column(Text)
    facial_asymmetry = Column(Text)
    mouth_opening_mm = Column(Float)
    clicking_pain = Column(Text)
    
    # Intraoral Examination - Soft Tissues
    soft_tissue_lips = Column(Text)
    soft_tissue_buccal_mucosa = Column(Text)
    soft_tissue_tongue = Column(Text)
    soft_tissue_floor_of_mouth = Column(Text)
    soft_tissue_palate = Column(Text)
    soft_tissue_gingiva = Column(Text)
    oral_hygiene_index = Column(String(50))
    
    # Intraoral Examination - Teeth
    missing_teeth = Column(Text)
    caries = Column(Text)
    discoloration = Column(Text)
    attrition_abrasion_erosion = Column(Text)
    mobility = Column(Text)
    malocclusion = Column(Text)
    occlusion_status = Column(Text)
    
    # Radiographic Findings
    radiographic_type = Column(String(100))  # IOPA, OPG, CBCT
    radiographic_observations = Column(Text)
    xray_image_path = Column(String(500))
    xray_analysis_result = Column(Text)  # ML model output JSON
    
    # Diagnosis
    provisional_diagnosis = Column(Text)
    differential_diagnosis = Column(Text)
    final_diagnosis = Column(Text)
    
    # Treatment Plan
    treatment_phase_1 = Column(Text)
    treatment_phase_2 = Column(Text)
    treatment_phase_3 = Column(Text)
    
    # Consent
    consent_obtained = Column(Boolean, default=False)
    consent_date = Column(DateTime)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    patient = relationship("Patient", back_populates="clinical_profiles")
    appointment = relationship("Appointment", back_populates="clinical_profile")
