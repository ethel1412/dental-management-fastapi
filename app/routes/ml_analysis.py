from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from app.services.ml_service import ml_service
from app.services.file_service import FileService
from app.models.user import User, UserRole
from app.utils.dependencies import require_role, get_current_user

router = APIRouter(prefix="/api/ml-analysis", tags=["ML Analysis"])


@router.post("/analyze-xray")
async def analyze_xray(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a panoramic dental X-ray and get instant AI analysis.
    Returns per-tooth FDI number, disease classification, severity,
    patient-friendly advice, and an annotated image (base64 JPEG).
    Available to ALL authenticated users (patients and doctors).
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image (JPEG/PNG).")

    file_path = await FileService.save_file(file, "xrays", "analysis")
    result = ml_service.analyze_xray(file_path)

    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result.get("message", "Analysis failed"))

    return {
        "message": "X-ray analysis completed",
        "user_id": current_user.id,
        "filename": file.filename,
        **result,
    }


@router.post("/analyze-xray-direct")
async def analyze_xray_direct(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),  # any authenticated user
):
    """Analyze X-ray without attaching to a clinical profile. Available to all authenticated users."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image (JPEG/PNG).")

    file_path = await FileService.save_file(file, "xrays", "temp")
    result = ml_service.analyze_xray(file_path)

    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result.get("message", "Analysis failed"))

    return {
        "message": "X-ray analysis completed",
        "result": result,
        "file_path": FileService.get_file_url(file_path),
    }


@router.get("/model-info")
def get_model_info(current_user: User = Depends(get_current_user)):
    """Get loaded model information."""
    return {
        "stage1": {
            "name": "Mask R-CNN (ResNet-50 FPN)",
            "purpose": "Tooth detection, segmentation, quadrant split, FDI numbering",
            "classes": 33,
            "status": "loaded" if ml_service.stage1_model else "not loaded",
        },
        "stage2": {
            "name": "ResNet-34 disease classifier",
            "purpose": "Per-tooth disease classification",
            "classes": ["Healthy", "Impacted", "Caries", "Periapical Lesion", "Deep Caries"],
            "status": "loaded" if ml_service.stage2_model else "not loaded",
        },
    }
