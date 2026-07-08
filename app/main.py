from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.database import engine, Base
from app.routes import (
    auth_router,
    doctor_router,
    clinic_router,
    lab_router,
    patient_router,
    appointment_router,
    clinical_profile_router,
    lab_order_router,
    payment_router,
    ml_analysis_router
)
from app.services.file_service import FileService
from app.config import settings
import os

# Create database tables
Base.metadata.create_all(bind=engine)

# Create upload directories
FileService.ensure_upload_dirs()

# NOTE: ML models are NOT loaded at startup.
# They are downloaded and loaded lazily on the first ML analysis request.
# This keeps startup memory well under the 512MB Render free tier limit.
# See app/services/ml_service.py for the lazy-load logic.

# Initialize FastAPI app
app = FastAPI(
    title="Dental Management System API",
    description="Comprehensive dental practice management system with ML-powered X-ray analysis",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Mount static files (uploads)
if os.path.exists(settings.UPLOAD_DIR):
    app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Include routers
app.include_router(auth_router)
app.include_router(doctor_router)
app.include_router(clinic_router)
app.include_router(lab_router)
app.include_router(patient_router)
app.include_router(appointment_router)
app.include_router(clinical_profile_router)
app.include_router(lab_order_router)
app.include_router(payment_router)
app.include_router(ml_analysis_router)

# Root endpoint
@app.get("/")
def read_root():
    return {
        "message": "Dental Management System API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/api/docs"
    }

# Health check endpoint
@app.get("/api/health")
def health_check():
    stage1 = os.path.exists(settings.STAGE1_MODEL_PATH)
    stage2 = os.path.exists(settings.STAGE2_MODEL_PATH)
    return {
        "status": "healthy",
        "database": "connected",
        "stage1_model": "on disk" if stage1 else "not downloaded yet",
        "stage2_model": "on disk" if stage2 else "not downloaded yet",
        "ml_note": "Models load lazily on first ML request to conserve memory"
    }


@app.on_event("startup")
async def startup_event():
    print("=" * 50)
    print("Dental Management System API Starting...")
    print("=" * 50)
    print(f"API Docs: /api/docs")
    print(f"Upload Directory: {settings.UPLOAD_DIR}")
    print("ML models will be loaded lazily on first analysis request.")
    print("=" * 50)


@app.on_event("shutdown")
async def shutdown_event():
    print("Shutting down Dental Management System API...")
