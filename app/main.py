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
import shutil

# Create database tables
Base.metadata.create_all(bind=engine)

# Create upload directories
FileService.ensure_upload_dirs()


def download_models():
    """Download ML model weights from Hugging Face Hub at startup.

    hf_hub_download() returns the actual path where the file landed.
    We copy it to the canonical path expected by settings so the rest
    of the code never has to care about HF's cache directory layout.
    """
    from huggingface_hub import hf_hub_download

    os.makedirs("app/ml_models", exist_ok=True)

    HF_REPO = "ethelrani/dental-models"

    if not os.path.exists(settings.STAGE1_MODEL_PATH):
        print("Downloading Stage 1 model (Mask R-CNN) from Hugging Face...")
        downloaded_path = hf_hub_download(
            repo_id=HF_REPO,
            filename="maskrcnn_teeth_best.pth",
            local_dir="app/ml_models",
            local_dir_use_symlinks=False,
        )
        # Ensure the file is at the canonical path
        if os.path.abspath(downloaded_path) != os.path.abspath(settings.STAGE1_MODEL_PATH):
            shutil.copy2(downloaded_path, settings.STAGE1_MODEL_PATH)
        print(f"Stage 1 model ready at {settings.STAGE1_MODEL_PATH}")
    else:
        print("Stage 1 model already exists, skipping download.")

    if not os.path.exists(settings.STAGE2_MODEL_PATH):
        print("Downloading Stage 2 model (Disease Classifier) from Hugging Face...")
        downloaded_path = hf_hub_download(
            repo_id=HF_REPO,
            filename="stage2_disease_best.pth",
            local_dir="app/ml_models",
            local_dir_use_symlinks=False,
        )
        if os.path.abspath(downloaded_path) != os.path.abspath(settings.STAGE2_MODEL_PATH):
            shutil.copy2(downloaded_path, settings.STAGE2_MODEL_PATH)
        print(f"Stage 2 model ready at {settings.STAGE2_MODEL_PATH}")
    else:
        print("Stage 2 model already exists, skipping download.")


# ── Download models BEFORE MLService singleton is created ──────────────────
try:
    download_models()
except Exception as e:
    print(f"Warning: Could not download models at import time: {e}")
    print("ML features will be unavailable until models are present.")

# ── NOW import the ML service (models are on disk) ──────────────────────────
from app.services.ml_service import ml_service  # noqa: E402

# If models were just downloaded but singleton was somehow already created
# with None models, reload them now.
if ml_service.stage1_model is None or ml_service.stage2_model is None:
    ml_service._load_models()

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
        "stage1_model": "loaded" if stage1 else "not found",
        "stage2_model": "loaded" if stage2 else "not found",
    }


@app.on_event("startup")
async def startup_event():
    print("=" * 50)
    print("Dental Management System API Starting...")
    print("=" * 50)
    print(f"API Docs: /api/docs")
    print(f"Upload Directory: {settings.UPLOAD_DIR}")
    print(f"Stage 1 model: {'loaded' if ml_service.stage1_model else 'NOT LOADED'}")
    print(f"Stage 2 model: {'loaded' if ml_service.stage2_model else 'NOT LOADED'}")
    print("=" * 50)


@app.on_event("shutdown")
async def shutdown_event():
    print("Shutting down Dental Management System API...")
