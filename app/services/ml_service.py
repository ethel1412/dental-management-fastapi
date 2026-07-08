# ML imports are deferred — torch/torchvision are NOT imported at module load time.
# They are imported the first time analyze_xray() is called.
# This keeps startup RAM under 512 MB on Render's free tier.

from typing import Dict, List, Optional
from app.config import settings
import os
import shutil

# ── Disease class map ────────────────────────────────────────────────────────
DISEASE_CLASSES = {
    0: "Healthy",
    1: "Impacted",
    2: "Caries",
    3: "Periapical Lesion",
    4: "Deep Caries",
}

DISEASE_COLORS_BGR = {
    "Healthy":           (100, 220,   0),
    "Impacted":          (  0, 100, 255),
    "Caries":            ( 50,  50, 255),
    "Deep Caries":       (200,   0, 200),
    "Periapical Lesion": (  0, 200, 255),
}

DISEASE_SEVERITY = {
    "Healthy":           "none",
    "Impacted":          "moderate",
    "Caries":            "mild",
    "Deep Caries":       "severe",
    "Periapical Lesion": "severe",
}

DISEASE_ADVICE = {
    "Healthy":           "This tooth appears healthy. Maintain regular brushing and flossing.",
    "Impacted":          "An impacted tooth may require orthodontic or surgical evaluation. Consult your dentist.",
    "Caries":            "Early-stage cavity detected. A dental filling is usually sufficient at this stage.",
    "Deep Caries":       "Advanced decay detected. Root canal treatment or crown may be needed. See a dentist soon.",
    "Periapical Lesion": "Infection at the tooth root detected. Prompt dental treatment is strongly advised.",
}

_TOOTH_TYPE_MAP: dict = {}
for _q_start, _labels in enumerate([range(1, 9), range(9, 17), range(17, 25), range(25, 33)]):
    for _pos, _lbl in enumerate(_labels, start=1):
        if _pos <= 2:
            _TOOTH_TYPE_MAP[_lbl] = "Incisor"
        elif _pos == 3:
            _TOOTH_TYPE_MAP[_lbl] = "Canine"
        elif _pos <= 5:
            _TOOTH_TYPE_MAP[_lbl] = "Premolar"
        else:
            _TOOTH_TYPE_MAP[_lbl] = "Molar"


def _tooth_type_from_label(label: int) -> str:
    return _TOOTH_TYPE_MAP.get(label, "Unknown")


QUADRANT_COLORS = [
    (255, 100,  60),
    ( 60, 180, 255),
    ( 60, 220,  80),
    (220, 100, 255),
]


def _download_models_if_needed():
    """Download model weights from Hugging Face on first use."""
    from huggingface_hub import hf_hub_download
    HF_REPO = "ethelrani/dental-models"
    os.makedirs("app/ml_models", exist_ok=True)

    if not os.path.exists(settings.STAGE1_MODEL_PATH):
        print("[ML] Downloading Stage 1 model (Mask R-CNN)...")
        downloaded = hf_hub_download(
            repo_id=HF_REPO,
            filename="maskrcnn_teeth_best.pth",
            local_dir="app/ml_models",
            local_dir_use_symlinks=False,
        )
        if os.path.abspath(downloaded) != os.path.abspath(settings.STAGE1_MODEL_PATH):
            shutil.copy2(downloaded, settings.STAGE1_MODEL_PATH)
        print(f"[ML] Stage 1 ready at {settings.STAGE1_MODEL_PATH}")

    if not os.path.exists(settings.STAGE2_MODEL_PATH):
        print("[ML] Downloading Stage 2 model (Disease Classifier)...")
        downloaded = hf_hub_download(
            repo_id=HF_REPO,
            filename="stage2_disease_best.pth",
            local_dir="app/ml_models",
            local_dir_use_symlinks=False,
        )
        if os.path.abspath(downloaded) != os.path.abspath(settings.STAGE2_MODEL_PATH):
            shutil.copy2(downloaded, settings.STAGE2_MODEL_PATH)
        print(f"[ML] Stage 2 ready at {settings.STAGE2_MODEL_PATH}")


class MLService:

    def __init__(self):
        # Do NOT load torch or models here — deferred to first call
        self.device = None
        self.stage1_model = None
        self.stage2_model = None
        self._models_loaded = False

    def _ensure_loaded(self):
        """Lazily download + load models on first use."""
        if self._models_loaded:
            return
        import torch
        import torchvision
        import torch.nn as nn
        from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
        from torchvision.models.detection.mask_rcnn import MaskRCNNPredictor

        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        print(f"[ML] Using device: {self.device}")

        try:
            _download_models_if_needed()
        except Exception as e:
            print(f"[ML] Model download failed: {e}")

        # Stage 1
        try:
            model = torchvision.models.detection.maskrcnn_resnet50_fpn(weights=None)
            in_feat = model.roi_heads.box_predictor.cls_score.in_features
            model.roi_heads.box_predictor = FastRCNNPredictor(in_feat, 33)
            in_feat_mask = model.roi_heads.mask_predictor.conv5_mask.in_channels
            model.roi_heads.mask_predictor = MaskRCNNPredictor(in_feat_mask, 256, 33)
            ckpt = torch.load(settings.STAGE1_MODEL_PATH, map_location=self.device, weights_only=False)
            state = ckpt['model_state_dict'] if isinstance(ckpt, dict) and 'model_state_dict' in ckpt else ckpt
            model.load_state_dict(state, strict=False)
            model.to(self.device).eval()
            self.stage1_model = model
            print("[ML] Stage 1 (Mask R-CNN) loaded")
        except Exception as e:
            print(f"[ML] Stage 1 load error: {e}")
            self.stage1_model = None

        # Stage 2
        try:
            model2 = torchvision.models.resnet34(weights=None)
            model2.fc = nn.Sequential(
                nn.Dropout(p=0.5),
                nn.Linear(model2.fc.in_features, 5),
            )
            ckpt2 = torch.load(settings.STAGE2_MODEL_PATH, map_location=self.device, weights_only=False)
            state2 = ckpt2['model_state_dict'] if isinstance(ckpt2, dict) and 'model_state_dict' in ckpt2 else ckpt2
            model2.load_state_dict(state2, strict=False)
            model2.to(self.device).eval()
            self.stage2_model = model2
            print("[ML] Stage 2 (ResNet-34 classifier) loaded")
        except Exception as e:
            print(f"[ML] Stage 2 load error: {e}")
            self.stage2_model = None

        self._models_loaded = True

    def _stage1_infer(self, img_tensor, conf: float = 0.5, iou_thr: float = 0.3):
        import torch
        from torchvision.ops import nms
        with torch.no_grad():
            raw = self.stage1_model([img_tensor.to(self.device)])[0]
        keep = raw['scores'] >= conf
        filt = {k: v[keep] for k, v in raw.items()}
        if len(filt['boxes']) > 0:
            idx = nms(filt['boxes'], filt['scores'], iou_thr)
            filt = {k: v[idx] for k, v in filt.items()}
        return filt

    def _classify_crop(self, pil_img):
        import torch
        from torchvision import transforms
        _transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ])
        tensor = _transform(pil_img).unsqueeze(0).to(self.device)
        with torch.no_grad():
            logits = self.stage2_model(tensor)
            probs = torch.softmax(logits, dim=1)[0].cpu().numpy()
        label = int(probs.argmax())
        return {
            "disease": DISEASE_CLASSES[label],
            "confidence": round(float(probs[label]), 4),
            "probabilities": {DISEASE_CLASSES[i]: round(float(p), 4) for i, p in enumerate(probs)},
        }

    @staticmethod
    def _assign_fdi(boxes_xyxy, img_w: int, img_h: int) -> List[int]:
        import numpy as np
        mid_x, mid_y = img_w / 2, img_h / 2
        quadrant_boxes: Dict[int, List] = {1: [], 2: [], 3: [], 4: []}
        for i, box in enumerate(boxes_xyxy):
            cx = (box[0] + box[2]) / 2
            cy = (box[1] + box[3]) / 2
            if cy <= mid_y and cx > mid_x:
                q = 1
            elif cy <= mid_y and cx <= mid_x:
                q = 2
            elif cy > mid_y and cx <= mid_x:
                q = 3
            else:
                q = 4
            quadrant_boxes[q].append((cx, i))
        fdi_start = {1: 11, 2: 21, 3: 31, 4: 41}
        index_result = [0] * len(boxes_xyxy)
        for q, items in quadrant_boxes.items():
            reverse = q in (2, 3)
            items_sorted = sorted(items, key=lambda t: t[0], reverse=reverse)
            for rank, (_, orig_idx) in enumerate(items_sorted):
                fdi = fdi_start[q] + rank
                index_result[orig_idx] = min(fdi, fdi_start[q] + 7)
        return index_result

    @staticmethod
    def _estimate_dental_age(labels_np) -> dict:
        unique_labels = set(int(l) for l in labels_np if 1 <= int(l) <= 32)
        n_teeth = len(unique_labels)
        third_molar_labels = {8, 16, 24, 32}
        has_third_molars = bool(unique_labels & third_molar_labels)
        if n_teeth == 0:
            return {"age_range": "Undetermined", "age_min": None, "age_max": None, "basis": "No teeth detected"}
        if n_teeth <= 10:
            return {"age_range": "5-9 years", "age_min": 5, "age_max": 9, "basis": "Likely deciduous dentition"}
        if n_teeth <= 20:
            return {"age_range": "6-12 years", "age_min": 6, "age_max": 12, "basis": "Mixed dentition stage"}
        if has_third_molars:
            if n_teeth >= 28:
                return {"age_range": "18-40 years", "age_min": 18, "age_max": 40, "basis": "Full adult dentition with third molars"}
            return {"age_range": "18-25 years", "age_min": 18, "age_max": 25, "basis": "Third molars detected"}
        return {"age_range": "13-20 years", "age_min": 13, "age_max": 20, "basis": "Full permanent dentition, no third molars"}

    @staticmethod
    def _image_to_b64(pil_img) -> str:
        import io, base64
        buf = io.BytesIO()
        pil_img.save(buf, format="JPEG", quality=88)
        return base64.b64encode(buf.getvalue()).decode()

    def analyze_xray(self, image_path: str) -> Dict:
        """Full pipeline. Lazily loads models on first call."""
        self._ensure_loaded()

        if self.stage1_model is None:
            return {"status": "error", "message": "Stage 1 model not available. Check model files and memory."}

        try:
            import torch
            import numpy as np
            import cv2
            from PIL import Image
            import torchvision.transforms.functional as TF

            pil_img = Image.open(image_path).convert("RGB")
            img_w, img_h = pil_img.size
            img_tensor = TF.to_tensor(pil_img)

            s1 = self._stage1_infer(img_tensor)
            boxes_np = s1['boxes'].cpu().numpy()
            masks_np = s1['masks'].cpu().numpy()
            scores_np = s1['scores'].cpu().numpy()
            labels_np = s1['labels'].cpu().numpy()

            fdi_list = self._assign_fdi(boxes_np, img_w, img_h)

            annotated = np.array(pil_img)[..., ::-1].copy()
            mid_x, mid_y = img_w // 2, img_h // 2
            cv2.line(annotated, (mid_x, 0), (mid_x, img_h), (255, 255, 255), 2)
            cv2.line(annotated, (0, mid_y), (img_w, mid_y), (255, 255, 255), 2)
            for label_txt, lx, ly in [("Q1", mid_x + 10, 20), ("Q2", 10, 20),
                                       ("Q3", 10, mid_y + 20), ("Q4", mid_x + 10, mid_y + 20)]:
                cv2.putText(annotated, label_txt, (lx, ly), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

            teeth_results = []
            summary_disease_counts: Dict[str, int] = {}

            for box, mask, score, fdi, s1_label in zip(boxes_np, masks_np, scores_np, fdi_list, labels_np):
                x1 = max(0, int(box[0]) - 10)
                y1 = max(0, int(box[1]) - 10)
                x2 = min(img_w, int(box[2]) + 10)
                y2 = min(img_h, int(box[3]) + 10)
                crop = pil_img.crop((x1, y1, x2, y2))

                if self.stage2_model is not None and crop.width > 4 and crop.height > 4:
                    cls_result = self._classify_crop(crop)
                else:
                    cls_result = {"disease": "Unknown", "confidence": 0.0, "probabilities": {}}

                disease = cls_result["disease"]
                color_bgr = DISEASE_COLORS_BGR.get(disease, (128, 128, 128))

                mask_bin = (mask[0] > 0.5).astype(np.uint8)
                color_layer = np.zeros_like(annotated)
                color_layer[mask_bin == 1] = color_bgr
                annotated = cv2.addWeighted(annotated, 1.0, color_layer, 0.45, 0)
                cv2.rectangle(annotated, (x1, y1), (x2, y2), color_bgr, 2)
                cv2.putText(annotated, str(fdi) if fdi else "?", (x1 + 2, y1 + 16),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, color_bgr, 2)
                if disease != "Healthy":
                    cv2.circle(annotated, (x2 - 6, y1 + 6), 6, (0, 0, 255), -1)

                summary_disease_counts[disease] = summary_disease_counts.get(disease, 0) + 1
                teeth_results.append({
                    "fdi_number": fdi,
                    "tooth_type": _tooth_type_from_label(int(s1_label)),
                    "detection_confidence": round(float(score), 4),
                    "bounding_box": {"x1": int(box[0]), "y1": int(box[1]), "x2": int(box[2]), "y2": int(box[3])},
                    "disease": disease,
                    "disease_confidence": cls_result["confidence"],
                    "disease_probabilities": cls_result["probabilities"],
                    "severity": DISEASE_SEVERITY.get(disease, "unknown"),
                    "advice": DISEASE_ADVICE.get(disease, ""),
                })

            age_estimate = self._estimate_dental_age(labels_np)
            type_counts: Dict[str, int] = {}
            for t in teeth_results:
                tt = t["tooth_type"]
                type_counts[tt] = type_counts.get(tt, 0) + 1

            total = len(teeth_results)
            diseased = sum(1 for t in teeth_results if t["disease"] != "Healthy")
            healthy = total - diseased

            if total == 0:
                overall_status = "no_teeth_detected"
            elif diseased == 0:
                overall_status = "all_healthy"
            elif diseased <= total * 0.25:
                overall_status = "mostly_healthy"
            elif diseased <= total * 0.5:
                overall_status = "moderate_issues"
            else:
                overall_status = "significant_issues"

            from PIL import Image as PILImage
            annotated_pil = PILImage.fromarray(annotated[..., ::-1])
            annotated_b64 = self._image_to_b64(annotated_pil)

            return {
                "status": "success",
                "summary": {
                    "total_teeth_detected": total,
                    "healthy_teeth": healthy,
                    "diseased_teeth": diseased,
                    "overall_status": overall_status,
                    "disease_breakdown": summary_disease_counts,
                    "tooth_type_breakdown": type_counts,
                    "age_estimate": age_estimate,
                },
                "teeth": teeth_results,
                "annotated_image_base64": annotated_b64,
                "model_info": {
                    "stage1": "Mask R-CNN (ResNet-50 FPN, 33 classes)",
                    "stage2": "ResNet-34 (5-class disease classifier)",
                    "device": str(self.device),
                },
            }

        except Exception as e:
            import traceback
            return {"status": "error", "message": str(e), "trace": traceback.format_exc()}

    def process_predictions(self, prediction: Dict) -> Dict:
        """Legacy helper kept for backward compat."""
        import numpy as np
        boxes = prediction['boxes'].cpu().numpy()
        labels = prediction['labels'].cpu().numpy()
        scores = prediction['scores'].cpu().numpy()
        masks = prediction['masks'].cpu().numpy()
        threshold = 0.5
        valid = scores >= threshold
        teeth = []
        for box, label, score, mask in zip(boxes[valid], labels[valid], scores[valid], masks[valid]):
            teeth.append({
                "tooth_id": int(label),
                "confidence": float(score),
                "bounding_box": {"x1": float(box[0]), "y1": float(box[1]),
                                  "x2": float(box[2]), "y2": float(box[3])},
                "mask_area": float(mask.sum()),
            })
        return {"total_teeth_detected": len(teeth), "teeth": teeth,
                "model_info": {"model_type": "Mask R-CNN", "device": str(self.device or "cpu")}}


# Global singleton — no torch imported yet
ml_service = MLService()
