"""Dental ML API — Gradio + ZeroGPU for HuggingFace Spaces.
Uses @spaces.GPU so inference runs on A100 (free ZeroGPU).
Also exposes POST /analyze as a REST endpoint for the Render backend proxy.
"""
# ── Patch huggingface_hub BEFORE gradio import ───────────────────────────────
# ZeroGPU base image ships huggingface_hub>=1.0 which removed HfFolder,
# but the base image also force-installs gradio[oauth]==4.44.0 which still
# imports HfFolder. This patch stubs it out so gradio loads cleanly.
import huggingface_hub as _hfhub
if not hasattr(_hfhub, 'HfFolder'):
    class _FakeHfFolder:
        @staticmethod
        def get_token(): return None
        @staticmethod
        def save_token(token): pass
        @staticmethod
        def delete_token(): pass
    _hfhub.HfFolder = _FakeHfFolder

import os, io, base64
import gradio as gr
import spaces
from huggingface_hub import hf_hub_download
from fastapi.responses import JSONResponse
from fastapi import UploadFile, File

STAGE1_PATH = "./ml_models/maskrcnn_teeth_best.pth"
STAGE2_PATH = "./ml_models/stage2_disease_best.pth"
HF_REPO     = "ethelrani/dental-models"

DISEASE_CLASSES    = {0:"Healthy",1:"Impacted",2:"Caries",3:"Periapical Lesion",4:"Deep Caries"}
DISEASE_COLORS_BGR = {"Healthy":(100,220,0),"Impacted":(0,100,255),"Caries":(50,50,255),"Deep Caries":(200,0,200),"Periapical Lesion":(0,200,255)}
DISEASE_SEVERITY   = {"Healthy":"none","Impacted":"moderate","Caries":"mild","Deep Caries":"severe","Periapical Lesion":"severe"}
DISEASE_ADVICE     = {
    "Healthy":           "This tooth appears healthy. Maintain regular brushing and flossing.",
    "Impacted":          "An impacted tooth may require orthodontic or surgical evaluation.",
    "Caries":            "Early-stage cavity detected. A dental filling is usually sufficient.",
    "Deep Caries":       "Advanced decay detected. Root canal or crown may be needed. See a dentist soon.",
    "Periapical Lesion": "Infection at the tooth root. Prompt dental treatment strongly advised.",
}

stage1_model = None
stage2_model = None
_loaded      = False


def _download_models():
    os.makedirs("ml_models", exist_ok=True)
    if not os.path.exists(STAGE1_PATH):
        print("[ML] Downloading Stage 1 model (Mask R-CNN)...")
        hf_hub_download(repo_id=HF_REPO, filename="maskrcnn_teeth_best.pth",
                        local_dir="ml_models", local_dir_use_symlinks=False)
        print("[ML] Stage 1 downloaded.")
    if not os.path.exists(STAGE2_PATH):
        print("[ML] Downloading Stage 2 model (ResNet-34)...")
        hf_hub_download(repo_id=HF_REPO, filename="stage2_disease_best.pth",
                        local_dir="ml_models", local_dir_use_symlinks=False)
        print("[ML] Stage 2 downloaded.")


def _ensure_loaded():
    global stage1_model, stage2_model, _loaded
    if _loaded:
        return
    import torch, torchvision, torch.nn as nn
    from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
    from torchvision.models.detection.mask_rcnn import MaskRCNNPredictor

    _download_models()

    # Stage 1 — Mask R-CNN (33 classes)
    try:
        m = torchvision.models.detection.maskrcnn_resnet50_fpn(weights=None)
        m.roi_heads.box_predictor = FastRCNNPredictor(
            m.roi_heads.box_predictor.cls_score.in_features, 33)
        m.roi_heads.mask_predictor = MaskRCNNPredictor(
            m.roi_heads.mask_predictor.conv5_mask.in_channels, 256, 33)
        ckpt = torch.load(STAGE1_PATH, map_location="cpu", weights_only=False)
        state = ckpt.get("model_state_dict", ckpt) if isinstance(ckpt, dict) else ckpt
        m.load_state_dict(state, strict=False)
        m.eval()
        stage1_model = m
        print("[ML] Stage 1 (Mask R-CNN) loaded OK")
    except Exception as e:
        print(f"[ML] Stage 1 load error: {e}")

    # Stage 2 — ResNet-34 (5 disease classes)
    try:
        m2 = torchvision.models.resnet34(weights=None)
        m2.fc = nn.Sequential(nn.Dropout(0.5), nn.Linear(m2.fc.in_features, 5))
        ckpt2 = torch.load(STAGE2_PATH, map_location="cpu", weights_only=False)
        state2 = ckpt2.get("model_state_dict", ckpt2) if isinstance(ckpt2, dict) else ckpt2
        m2.load_state_dict(state2, strict=False)
        m2.eval()
        stage2_model = m2
        print("[ML] Stage 2 (ResNet-34) loaded OK")
    except Exception as e:
        print(f"[ML] Stage 2 load error: {e}")

    _loaded = True


@spaces.GPU
def _run_inference(image_bytes: bytes) -> dict:
    """Full pipeline. @spaces.GPU allocates A100 for the duration of this call."""
    import torch, numpy as np, cv2
    from PIL import Image
    import torchvision.transforms.functional as TF
    from torchvision.ops import nms
    from torchvision import transforms as T

    _ensure_loaded()

    if stage1_model is None:
        return {"status": "error", "message": "Stage 1 model failed to load."}

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    stage1_model.to(device)
    if stage2_model is not None:
        stage2_model.to(device)

    pil = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    W, H = pil.size
    t = TF.to_tensor(pil).to(device)

    with torch.no_grad():
        raw = stage1_model([t])[0]

    keep = raw["scores"] >= 0.5
    filt = {k: v[keep] for k, v in raw.items()}
    if len(filt["boxes"]) > 0:
        idx = nms(filt["boxes"], filt["scores"], 0.3)
        filt = {k: v[idx] for k, v in filt.items()}

    boxes  = filt["boxes"].cpu().numpy()
    masks  = filt["masks"].cpu().numpy()
    scores = filt["scores"].cpu().numpy()

    # FDI quadrant assignment
    mid_x, mid_y = W / 2, H / 2
    q_boxes = {1: [], 2: [], 3: [], 4: []}
    for i, b in enumerate(boxes):
        cx, cy = (b[0]+b[2])/2, (b[1]+b[3])/2
        q = 1 if cy<=mid_y and cx>mid_x else 2 if cy<=mid_y else 3 if cx<=mid_x else 4
        q_boxes[q].append((cx, i))
    fdi_start = {1: 11, 2: 21, 3: 31, 4: 41}
    fdi_list  = [0] * len(boxes)
    for q, items in q_boxes.items():
        for rank, (_, oi) in enumerate(sorted(items, key=lambda x: x[0], reverse=q in (2, 3))):
            fdi_list[oi] = min(fdi_start[q] + rank, fdi_start[q] + 7)

    # Annotate image
    annotated = np.array(pil)[..., ::-1].copy()
    cv2.line(annotated, (int(mid_x), 0), (int(mid_x), H), (255, 255, 255), 2)
    cv2.line(annotated, (0, int(mid_y)), (W, int(mid_y)), (255, 255, 255), 2)
    for lbl, lx, ly in [("Q1", int(mid_x)+10, 20), ("Q2", 10, 20),
                         ("Q3", 10, int(mid_y)+20), ("Q4", int(mid_x)+10, int(mid_y)+20)]:
        cv2.putText(annotated, lbl, (lx, ly), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)

    tf = T.Compose([
        T.Resize((224, 224)),
        T.ToTensor(),
        T.Normalize([.485, .456, .406], [.229, .224, .225])
    ])
    teeth, disease_counts = [], {}

    for box, mask, score, fdi in zip(boxes, masks, scores, fdi_list):
        x1 = max(0, int(box[0])-10); y1 = max(0, int(box[1])-10)
        x2 = min(W, int(box[2])+10); y2 = min(H, int(box[3])+10)
        crop = pil.crop((x1, y1, x2, y2))

        if stage2_model is not None and crop.width > 4 and crop.height > 4:
            with torch.no_grad():
                tensor = tf(crop).unsqueeze(0).to(device)
                p = torch.softmax(stage2_model(tensor), 1)[0].cpu().numpy()
            li = int(p.argmax())
            cls_r = {
                "disease":    DISEASE_CLASSES[li],
                "confidence": round(float(p[li]), 4),
                "probabilities": {DISEASE_CLASSES[i]: round(float(v), 4) for i, v in enumerate(p)}
            }
        else:
            cls_r = {"disease": "Unknown", "confidence": 0.0, "probabilities": {}}

        d   = cls_r["disease"]
        col = DISEASE_COLORS_BGR.get(d, (128, 128, 128))
        mb  = (mask[0] > 0.5).astype(np.uint8)
        cl  = np.zeros_like(annotated)
        cl[mb == 1] = col
        annotated = cv2.addWeighted(annotated, 1.0, cl, 0.45, 0)
        cv2.rectangle(annotated, (x1, y1), (x2, y2), col, 2)
        cv2.putText(annotated, str(fdi) if fdi else "?", (x1+2, y1+16),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, col, 2)
        if d != "Healthy":
            cv2.circle(annotated, (x2-6, y1+6), 6, (0, 0, 255), -1)

        disease_counts[d] = disease_counts.get(d, 0) + 1
        teeth.append({
            "fdi_number":           fdi,
            "detection_confidence": round(float(score), 4),
            "bounding_box":         {"x1": int(box[0]), "y1": int(box[1]), "x2": int(box[2]), "y2": int(box[3])},
            "disease":              d,
            "disease_confidence":   cls_r["confidence"],
            "disease_probabilities": cls_r["probabilities"],
            "severity":             DISEASE_SEVERITY.get(d, "unknown"),
            "advice":               DISEASE_ADVICE.get(d, ""),
        })

    total    = len(teeth)
    diseased = sum(1 for t in teeth if t["disease"] != "Healthy")
    status   = ("no_teeth_detected" if total == 0 else
                "all_healthy"       if diseased == 0 else
                "mostly_healthy"    if diseased <= total * .25 else
                "moderate_issues"   if diseased <= total * .5 else
                "significant_issues")

    from PIL import Image as PILImage
    out_pil = PILImage.fromarray(annotated[..., ::-1])
    buf = io.BytesIO()
    out_pil.save(buf, format="JPEG", quality=88)
    b64 = base64.b64encode(buf.getvalue()).decode()

    return {
        "status": "success",
        "summary": {
            "total_teeth_detected": total,
            "healthy_teeth":        total - diseased,
            "diseased_teeth":       diseased,
            "overall_status":       status,
            "disease_breakdown":    disease_counts,
        },
        "teeth":                  teeth,
        "annotated_image_base64": b64,
        "model_info": {
            "stage1": "Mask R-CNN (ResNet-50 FPN, 33 classes)",
            "stage2": "ResNet-34 (5-class disease classifier)",
            "device": str(device),
        },
    }


# ── Gradio UI wrapper ────────────────────────────────────────────────────────
def gradio_analyze(pil_image):
    buf = io.BytesIO()
    pil_image.save(buf, format="JPEG")
    result = _run_inference(buf.getvalue())
    import json
    return json.dumps(result, indent=2)


demo = gr.Interface(
    fn=gradio_analyze,
    inputs=gr.Image(type="pil", label="Upload Dental X-ray (JPEG/PNG)"),
    outputs=gr.Textbox(label="Analysis Result (JSON)", lines=30),
    title="\U0001f9b7 Dental X-ray Analysis API",
    description=(
        "**Stage 1** — Mask R-CNN (ResNet-50 FPN): detects & segments teeth, assigns FDI numbers.\n"
        "**Stage 2** — ResNet-34: classifies each tooth as Healthy / Caries / Deep Caries / Impacted / Periapical Lesion.\n\n"
        "REST endpoint also available: `POST /analyze` with `multipart/form-data` field `file`."
    ),
    allow_flagging="never",
)

app = demo.app


@app.post("/analyze")
async def analyze_api(file: UploadFile = File(...)):
    image_bytes = await file.read()
    result = _run_inference(image_bytes)
    return JSONResponse(result)


@app.get("/health")
async def health():
    return {"status": "ok", "loaded": _loaded}


if __name__ == "__main__":
    demo.launch(server_port=7860)
