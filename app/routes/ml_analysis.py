from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from app.services.ml_service import ml_service
from app.services.file_service import FileService
from app.models.user import User, UserRole
from app.utils.dependencies import require_role

router = APIRouter(prefix="/api/ml-analysis", tags=["ML Analysis"])

@router.post("/analyze-xray-direct")
async def analyze_xray_direct(
    file: UploadFile = File(...),
    current_user: User = Depends(require_role([UserRole.DOCTOR]))
):
    """Analyze X-ray directly without saving to clinical profile"""
    # Save temporary file
    file_path = await FileService.save_file(file, "xrays", "temp")
    
    # Run ML analysis
    analysis_result = ml_service.analyze_xray(file_path)
    
    return {
        "message": "X-ray analysis completed",
        "result": analysis_result,
        "file_path": FileService.get_file_url(file_path)
    }

@router.get("/model-info")
def get_model_info(current_user: User = Depends(require_role([UserRole.DOCTOR]))):
    """Get ML model information"""
    return {
        "model_type": "Mask R-CNN",
        "model_name": "maskrcnn_teeth_segmentation",
        "purpose": "Dental X-ray teeth segmentation and detection",
        "framework": "PyTorch",
        "status": "loaded" if ml_service.model else "not loaded"
    }
