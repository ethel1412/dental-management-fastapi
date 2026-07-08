import httpx
import os
import base64
import json
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from app.models.user import User
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/api/ml-analysis", tags=["ML Analysis"])

# Set HF_SPACE_URL as an env var on Render, e.g.:
# https://ethelrani-dental-ml-api.hf.space
HF_SPACE_URL = os.getenv("HF_SPACE_URL", "").rstrip("/")


def _check_space_configured():
    if not HF_SPACE_URL:
        raise HTTPException(
            status_code=503,
            detail="ML service not configured. Set HF_SPACE_URL environment variable on Render.",
        )


async def _proxy_analyze(file: UploadFile) -> dict:
    """
    Forward the image to the HuggingFace Gradio Space.
    Tries Gradio 6.x path first (/gradio_api/run/predict),
    falls back to legacy path (/run/predict).
    """
    _check_space_configured()
    image_bytes = await file.read()

    content_type = file.content_type or "image/jpeg"
    b64 = base64.b64encode(image_bytes).decode()
    data_uri = f"data:{content_type};base64,{b64}"
    payload = {"data": [data_uri]}

    # Gradio 6.x uses /gradio_api/run/predict, older uses /run/predict
    endpoints = [
        f"{HF_SPACE_URL}/gradio_api/run/predict",
        f"{HF_SPACE_URL}/run/predict",
    ]

    last_error = None
    async with httpx.AsyncClient(timeout=300.0) as client:
        for endpoint in endpoints:
            try:
                response = await client.post(
                    endpoint,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
                if response.status_code == 200:
                    break
                last_error = f"[{endpoint}] HTTP {response.status_code}: {response.text[:200]}"
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
        else:
            raise HTTPException(status_code=502, detail=f"ML service error on all endpoints. Last: {last_error}")

    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"ML service error: {response.text[:500]}",
        )

    # Gradio returns {"data": ["<json string>"]}
    gradio_response = response.json()
    raw = gradio_response.get("data", [None])[0]
    if raw is None:
        raise HTTPException(status_code=502, detail=f"Empty response from ML service. Full response: {str(gradio_response)[:300]}")

    try:
        result = json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        raise HTTPException(status_code=502, detail=f"Could not parse ML response: {str(raw)[:300]}")

    return result


@router.post("/analyze-xray")
async def analyze_xray(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a panoramic dental X-ray and get instant AI analysis.
    Proxies to HuggingFace Gradio Space for inference.
    """
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
    """Analyze X-ray without attaching to a clinical profile."""
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
    """Get loaded model status from HuggingFace Space."""
    _check_space_configured()
    space_status = "unknown"
    async with httpx.AsyncClient(timeout=15.0) as client:
        for path in ["/gradio_api/info", "/info"]:
            try:
                response = await client.get(f"{HF_SPACE_URL}{path}")
                if response.status_code == 200:
                    space_status = "running"
                    break
            except Exception:
                continue
        else:
            space_status = "unreachable"

    return {
        "stage1": {
            "name": "Mask R-CNN (ResNet-50 FPN)",
            "purpose": "Tooth detection, segmentation, quadrant split, FDI numbering",
            "classes": 33,
        },
        "stage2": {
            "name": "ResNet-34 disease classifier",
            "purpose": "Per-tooth disease classification",
            "classes": ["Healthy", "Impacted", "Caries", "Periapical Lesion", "Deep Caries"],
        },
        "inference_host": HF_SPACE_URL or "not configured",
        "space_status": space_status,
    }
