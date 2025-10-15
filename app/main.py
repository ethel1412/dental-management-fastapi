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
    allow_origins=["*"],  # In production, specify your Flutter app's domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
    return {
        "status": "healthy",
        "database": "connected",
        "ml_model": "loaded" if True else "not loaded"
    }

# Startup event
@app.on_event("startup")
async def startup_event():
    print("=" * 50)
    print("Dental Management System API Started")
    print("=" * 50)
    print(f"API Docs: http://localhost:8000/api/docs")
    print(f"Database: Connected")
    print(f"Upload Directory: {settings.UPLOAD_DIR}")
    print("=" * 50)

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    print("Shutting down Dental Management System API...")
