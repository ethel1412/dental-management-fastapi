import os
import json
import tempfile
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.concurrency import run_in_threadpool
from app.models.user import User
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/api/ml-analysis", tags=["ML Analysis"])

HF_SPACE_URL = os.getenv("HF_SPACE_URL", "").rstrip("/")
HF_TOKEN = os.getenv("HF_TOKEN")  # only needed if the Space is private


def _check_space_configured():
    if not HF_SPACE_URL:
        raise HTTPException(
            status_code=503,
            detail="ML service not configured. Set HF_SPACE_URL environment variable on Render.",
        )


def _get_client():
    """
    Lazily import + construct gradio_client.Client.
    Deferred import keeps gradio_client's own deps off the FastAPI cold-start path.
    """
    from gradio_client import Client
    return Client(HF_SPACE_URL, hf_token=HF_TOKEN) if HF_TOKEN else Client(HF_SPACE_URL)


def _predict_sync(tmp_path: str) -> dict:
    """
    Blocking call — gradio_client is synchronous. Always call this via
    run_in_threadpool from an async route, never directly, or it will
    block the whole event loop for the duration of the HF Space's
    inference (which can be 10-60s on ZeroGPU cold start).
    """
    from gradio_client import handle_file
    client = _get_client()
    result = client.predict(
        handle_file(tmp_path),
        api_name="/analyze",
    )
    # The Space's gradio_analyze() returns a JSON string (see hf_space/app.py)
    return json.loads(result)


async def _proxy_analyze(file: UploadFile) -> dict:
    _check_space_configured()
    image_bytes = await file.read()

    suffix = os.path.splitext(file.filename or "xray.jpg")[1] or ".jpg"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(image_bytes)
        tmp_path = tmp.name

    try:
        try:
            result = await run_in_threadpool(_predict_sync, tmp_path)
        except Exception as e:
            # Cold-start / queue timeouts on ZeroGPU show up as generic
            # exceptions from gradio_client, not clean HTTP status codes —
            # normalize them into a retryable 503 rather than a raw 500.
            raise HTTPException(
                status_code=503,
                detail=f"ML service unavailable or still starting up — please retry in 30-60s. ({e})",
            )
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    if not isinstance(result, dict) or result.get("status") == "error":
        raise HTTPException(
            status_code=502,
            detail=f"ML service returned an error: {result.get('message', 'unknown error') if isinstance(result, dict) else result}",
        )

    return result


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
    try:
        await run_in_threadpool(_get_client)
        space_status = "reachable"
    except Exception:
        space_status = "unreachable"
    return {
        "stage1": {"name": "Mask R-CNN (ResNet-50 FPN)", "classes": 33},
        "stage2": {"name": "ResNet-34 disease classifier",
                   "classes": ["Healthy", "Impacted", "Caries", "Periapical Lesion", "Deep Caries"]},
        "inference_host": HF_SPACE_URL or "not configured",
        "space_status": space_status,
    }