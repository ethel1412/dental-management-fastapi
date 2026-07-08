import httpx
import os
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from app.models.user import User
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/api/ml-analysis", tags=["ML Analysis"])

HF_SPACE_URL = os.getenv("HF_SPACE_URL", "").rstrip("/")


def _check_space_configured():
    if not HF_SPACE_URL:
        raise HTTPException(
            status_code=503,
            detail="ML service not configured. Set HF_SPACE_URL environment variable on Render.",
        )


async def _proxy_analyze(file: UploadFile) -> dict:
    """
    Forward the image to the HuggingFace Space plain REST /analyze endpoint.
    Simple multipart upload — no Gradio predict API involved.
    """
    _check_space_configured()
    image_bytes = await file.read()

    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            response = await client.post(
                f"{HF_SPACE_URL}/analyze",
                files={"file": (file.filename or "xray.jpg", image_bytes, file.content_type or "image/jpeg")},
            )
        except httpx.ConnectError:
            raise HTTPException(
                status_code=503,
                detail="Could not connect to ML service. The Space may be waking up — please retry in 30 seconds.",
            )
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=504,
                detail="ML service timed out. The models may still be loading — please retry.",
            )

    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"ML service error: {response.text[:500]}",
        )

    return response.json()


@router.post("/analyze-xray")
async def analyze_xray(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image (JPEG/PNG).")
    result = await _proxy_analyze(file)
    return {
        "message": "X-ray analysis completed",
        "user_id": current_user.id,
        "filename": file.filename,
        **result,
    }


@router.post("/analyze-xray-direct")
async def analyze_xray_direct(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image (JPEG/PNG).")
    result = await _proxy_analyze(file)
    return {
        "message": "X-ray analysis completed",
        "user_id": current_user.id,
        "filename": file.filename,
        **result,
    }


@router.get("/model-info")
async def get_model_info(current_user: User = Depends(get_current_user)):
    _check_space_configured()
    space_status = "unknown"
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.get(f"{HF_SPACE_URL}/health")
            space_status = "running" if response.status_code == 200 else "unreachable"
        except Exception:
            space_status = "unreachable"
    return {
        "stage1": {"name": "Mask R-CNN (ResNet-50 FPN)", "classes": 33},
        "stage2": {"name": "ResNet-34 disease classifier",
                   "classes": ["Healthy", "Impacted", "Caries", "Periapical Lesion", "Deep Caries"]},
        "inference_host": HF_SPACE_URL or "not configured",
        "space_status": space_status,
    }
