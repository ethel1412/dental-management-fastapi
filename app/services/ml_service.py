import torch
import torch.nn as nn
import torchvision
import torchvision.transforms.functional as TF
from torchvision import transforms
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
from torchvision.models.detection.mask_rcnn import MaskRCNNPredictor
from torchvision.ops import nms
from PIL import Image
import numpy as np
import cv2
import io
import base64
from typing import Dict, List, Optional
from app.config import settings

# ── Disease class map (matches Stage 2 v7 training) ──────────────────────────
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

# ── Tooth type derived from Stage 1 class label (1–32) ───────────────────────
# Labels follow the HumansInTheLoop dataset ordering: upper arch labels 1–16,
# lower arch labels 17–32, each sequenced from patient's right to left.
# FDI positions per quadrant: 1–2 incisors, 3 canine, 4–5 premolars, 6–8 molars.
_TOOTH_TYPE_MAP: dict[int, str] = {}
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
    """Return anatomical tooth type from Stage 1 class label (1–32)."""
    return _TOOTH_TYPE_MAP.get(label, "Unknown")

# ── Quadrant colours for segmentation overlay ────────────────────────────────
QUADRANT_COLORS = [
    (255, 100,  60),   # Q1 – upper right (orange-red)
    ( 60, 180, 255),   # Q2 – upper left  (sky blue)
    ( 60, 220,  80),   # Q3 – lower left  (green)
    (220, 100, 255),   # Q4 – lower right (violet)
]


class MLService:

    def __init__(self):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.stage1_model: Optional[torch.nn.Module] = None
        self.stage2_model: Optional[torch.nn.Module] = None
        self._load_models()

    # ── Model loaders ──────────────────────────────────────────────────────

    def _build_stage1(self, num_classes: int = 33) -> torch.nn.Module:
        model = torchvision.models.detection.maskrcnn_resnet50_fpn(weights=None)
        in_feat = model.roi_heads.box_predictor.cls_score.in_features
        model.roi_heads.box_predictor = FastRCNNPredictor(in_feat, num_classes)
        in_feat_mask = model.roi_heads.mask_predictor.conv5_mask.in_channels
        model.roi_heads.mask_predictor = MaskRCNNPredictor(in_feat_mask, 256, num_classes)
        return model

    def _build_stage2(self, num_classes: int = 5) -> torch.nn.Module:
        model = torchvision.models.resnet34(weights=None)
        model.fc = nn.Sequential(
            nn.Dropout(p=0.5),
            nn.Linear(model.fc.in_features, num_classes),
        )
        return model

    def _load_models(self):
        # Stage 1
        try:
            ckpt = torch.load(settings.STAGE1_MODEL_PATH, map_location=self.device, weights_only=False)
            self.stage1_model = self._build_stage1(num_classes=33)
            state = ckpt['model_state_dict'] if isinstance(ckpt, dict) and 'model_state_dict' in ckpt else ckpt
            self.stage1_model.load_state_dict(state, strict=False)
            self.stage1_model.to(self.device).eval()
            print(f"[ML] Stage 1 (Mask R-CNN) loaded on {self.device}")
        except Exception as e:
            print(f"[ML] Stage 1 load error: {e}")
            self.stage1_model = None

        # Stage 2
        try:
            ckpt2 = torch.load(settings.STAGE2_MODEL_PATH, map_location=self.device, weights_only=False)
            self.stage2_model = self._build_stage2(num_classes=5)
            state2 = ckpt2['model_state_dict'] if isinstance(ckpt2, dict) and 'model_state_dict' in ckpt2 else ckpt2
            self.stage2_model.load_state_dict(state2, strict=False)
            self.stage2_model.to(self.device).eval()
            print(f"[ML] Stage 2 (ResNet-34 classifier) loaded on {self.device}")
        except Exception as e:
            print(f"[ML] Stage 2 load error: {e}")
            self.stage2_model = None

    # ── Stage 1 inference ─────────────────────────────────────────────────

    def _stage1_infer(self, img_tensor: torch.Tensor, conf: float = 0.5, iou_thr: float = 0.3):
        with torch.no_grad():
            raw = self.stage1_model([img_tensor.to(self.device)])[0]
        keep = raw['scores'] >= conf
        filt = {k: v[keep] for k, v in raw.items()}
        if len(filt['boxes']) > 0:
            idx = nms(filt['boxes'], filt['scores'], iou_thr)
            filt = {k: v[idx] for k, v in filt.items()}
        return filt

    # ── Stage 2 inference on a single crop ────────────────────────────────

    _stage2_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])

    def _classify_crop(self, pil_img: Image.Image) -> Dict:
        tensor = self._stage2_transform(pil_img).unsqueeze(0).to(self.device)
        with torch.no_grad():
            logits = self.stage2_model(tensor)
            probs = torch.softmax(logits, dim=1)[0].cpu().numpy()
        label = int(probs.argmax())
        return {
            "disease": DISEASE_CLASSES[label],
            "confidence": round(float(probs[label]), 4),
            "probabilities": {
                DISEASE_CLASSES[i]: round(float(p), 4)
                for i, p in enumerate(probs)
            },
        }

    # ── FDI tooth numbering ────────────────────────────────────────────────
    # Stage 1 labels 1..32 (background = 0) mapped to FDI notation.
    # We use image-midpoint quadrant split to assign Q1-Q4 and then
    # number each tooth within its quadrant by x-position.

    @staticmethod
    def _assign_fdi(boxes_xyxy: np.ndarray, img_w: int, img_h: int) -> List[int]:
        """Return FDI tooth number for each box."""
        mid_x, mid_y = img_w / 2, img_h / 2
        fdi_numbers = []
        # Group boxes per quadrant first so we can rank by position
        quadrant_boxes: Dict[int, List] = {1: [], 2: [], 3: [], 4: []}
        for i, box in enumerate(boxes_xyxy):
            cx = (box[0] + box[2]) / 2
            cy = (box[1] + box[3]) / 2
            # Patient's right = image left (cx < mid_x)
            if cy <= mid_y and cx > mid_x:
                q = 1   # upper right
            elif cy <= mid_y and cx <= mid_x:
                q = 2   # upper left
            elif cy > mid_y and cx <= mid_x:
                q = 3   # lower left
            else:
                q = 4   # lower right
            quadrant_boxes[q].append((cx, i))

        # FDI: Q1 = 11-18, Q2 = 21-28, Q3 = 31-38, Q4 = 41-48
        fdi_start = {1: 11, 2: 21, 3: 31, 4: 41}
        index_result = [0] * len(boxes_xyxy)
        for q, items in quadrant_boxes.items():
            # Within Q1/Q4 sort ascending cx (incisor→molar away from midline)
            # Within Q2/Q3 sort descending cx
            reverse = q in (2, 3)
            items_sorted = sorted(items, key=lambda t: t[0], reverse=reverse)
            for rank, (_, orig_idx) in enumerate(items_sorted):
                fdi = fdi_start[q] + rank
                index_result[orig_idx] = min(fdi, fdi_start[q] + 7)  # cap at 8 teeth/quadrant
        return index_result

    # ── Dental age estimation ──────────────────────────────────────────────
    # Rule-based heuristic derived from eruption patterns and FDI tooth presence.
    # Labels 1–32 map to specific teeth; third molars are labels 7, 8 (UR), 15, 16 (UL),
    # 23, 24 (LL), 31, 32 (LR) depending on dataset ordering — conservatively we flag
    # the last positional slot in each quadrant as a wisdom tooth candidate.

    @staticmethod
    def _estimate_dental_age(labels_np) -> dict:
        """
        Estimate patient age range from detected tooth labels (1–32).

        Rules (per standard eruption charts):
        - Deciduous only (very few teeth, all small):      5–9 years
        - Mixed dentition (some permanent, some missing):  6–12 years
        - Full permanent, no third molars visible:         13–20 years
        - Third molars present:                            18+ years
        - Full adult arch (28–32 teeth):                   18–40 years
        """
        unique_labels = set(int(l) for l in labels_np if 1 <= int(l) <= 32)
        n_teeth = len(unique_labels)

        # Third molars: positional slots 8, 16, 17, 25 in standard FDI ordering
        # In the HumansInTheLoop dataset labels 1–32 sequenced per quadrant —
        # labels at positions 8, 16, 24, 32 are the most posterior (wisdom teeth).
        third_molar_labels = {8, 16, 24, 32}
        has_third_molars = bool(unique_labels & third_molar_labels)

        if n_teeth == 0:
            return {"age_range": "Undetermined", "age_min": None, "age_max": None,
                    "basis": "No teeth detected"}

        if n_teeth <= 10:
            return {"age_range": "5–9 years", "age_min": 5, "age_max": 9,
                    "basis": "Few teeth detected — likely deciduous or early mixed dentition"}

        if n_teeth <= 20:
            return {"age_range": "6–12 years", "age_min": 6, "age_max": 12,
                    "basis": "Partial dentition — consistent with mixed dentition stage"}

        if has_third_molars:
            if n_teeth >= 28:
                return {"age_range": "18–40 years", "age_min": 18, "age_max": 40,
                        "basis": "Full adult dentition with third molars present"}
            return {"age_range": "18–25 years", "age_min": 18, "age_max": 25,
                    "basis": "Third molars detected — patient is likely an adult"}

        return {"age_range": "13–20 years", "age_min": 13, "age_max": 20,
                "basis": "Full permanent dentition without visible third molars"}

    # ── Annotated image builder ────────────────────────────────────────────

    @staticmethod
    def _image_to_b64(pil_img: Image.Image) -> str:
        buf = io.BytesIO()
        pil_img.save(buf, format="JPEG", quality=88)
        return base64.b64encode(buf.getvalue()).decode()

    # ── Main pipeline ─────────────────────────────────────────────────────

    def analyze_xray(self, image_path: str) -> Dict:
        """Full Stage 1 + Stage 2 pipeline. Returns structured result + annotated image."""
        if self.stage1_model is None:
            return {"status": "error", "message": "Stage 1 model not loaded"}

        try:
            pil_img = Image.open(image_path).convert("RGB")
            img_w, img_h = pil_img.size
            img_tensor = TF.to_tensor(pil_img)

            # ── Stage 1: detect all teeth ─────────────────────────────────
            s1 = self._stage1_infer(img_tensor)
            boxes_np = s1['boxes'].cpu().numpy()      # (N, 4) xyxy
            masks_np = s1['masks'].cpu().numpy()      # (N, 1, H, W)
            scores_np = s1['scores'].cpu().numpy()
            labels_np = s1['labels'].cpu().numpy()    # (N,) Stage 1 class labels 1–32

            fdi_list = self._assign_fdi(boxes_np, img_w, img_h)

            # Build annotated image (numpy BGR)
            annotated = np.array(pil_img)[..., ::-1].copy()  # RGB → BGR
            mid_x, mid_y = img_w // 2, img_h // 2

            # Draw quadrant dividers
            cv2.line(annotated, (mid_x, 0), (mid_x, img_h), (255, 255, 255), 2)
            cv2.line(annotated, (0, mid_y), (img_w, mid_y), (255, 255, 255), 2)
            for i, label in enumerate([("Q1", mid_x + 10, 20), ("Q2", 10, 20),
                                        ("Q3", 10, mid_y + 20), ("Q4", mid_x + 10, mid_y + 20)]):
                cv2.putText(annotated, label[0], (label[1], label[2]),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

            # ── Stage 2: classify each tooth crop ─────────────────────────
            teeth_results = []
            summary_disease_counts: Dict[str, int] = {}

            for i, (box, mask, score, fdi, s1_label) in enumerate(zip(boxes_np, masks_np, scores_np, fdi_list, labels_np)):
                x1, y1, x2, y2 = (
                    max(0, int(box[0]) - 10),
                    max(0, int(box[1]) - 10),
                    min(img_w, int(box[2]) + 10),
                    min(img_h, int(box[3]) + 10),
                )
                crop = pil_img.crop((x1, y1, x2, y2))

                if self.stage2_model is not None and crop.width > 4 and crop.height > 4:
                    cls_result = self._classify_crop(crop)
                else:
                    cls_result = {"disease": "Unknown", "confidence": 0.0, "probabilities": {}}

                disease = cls_result["disease"]
                color_bgr = DISEASE_COLORS_BGR.get(disease, (128, 128, 128))

                # Draw segmentation mask overlay
                mask_bin = (mask[0] > 0.5).astype(np.uint8)
                color_layer = np.zeros_like(annotated)
                color_layer[mask_bin == 1] = color_bgr
                annotated = cv2.addWeighted(annotated, 1.0, color_layer, 0.45, 0)

                # Draw bounding box
                cv2.rectangle(annotated, (x1, y1), (x2, y2), color_bgr, 2)

                # Draw FDI label
                label_txt = f"{fdi}" if fdi else "?"
                cv2.putText(annotated, label_txt, (x1 + 2, y1 + 16),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, color_bgr, 2)

                # Disease indicator dot (top-right of box)
                if disease != "Healthy":
                    cv2.circle(annotated, (x2 - 6, y1 + 6), 6, (0, 0, 255), -1)

                summary_disease_counts[disease] = summary_disease_counts.get(disease, 0) + 1

                teeth_results.append({
                    "fdi_number": fdi,
                    "tooth_type": _tooth_type_from_label(int(s1_label)),
                    "detection_confidence": round(float(score), 4),
                    "bounding_box": {"x1": int(box[0]), "y1": int(box[1]),
                                     "x2": int(box[2]), "y2": int(box[3])},
                    "disease": disease,
                    "disease_confidence": cls_result["confidence"],
                    "disease_probabilities": cls_result["probabilities"],
                    "severity": DISEASE_SEVERITY.get(disease, "unknown"),
                    "advice": DISEASE_ADVICE.get(disease, ""),
                })

            # ── Dental age estimation ──────────────────────────────────────
            age_estimate = self._estimate_dental_age(labels_np)

            # ── Type breakdown ─────────────────────────────────────────────
            type_counts: Dict[str, int] = {}
            for t in teeth_results:
                tt = t["tooth_type"]
                type_counts[tt] = type_counts.get(tt, 0) + 1

            # Overall health summary
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

            # Convert annotated image to base64
            annotated_pil = Image.fromarray(annotated[..., ::-1])  # BGR → RGB
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
                    "stage2": "ResNet-34 (5-class: Healthy/Impacted/Caries/Periapical/DeepCaries)",
                    "device": str(self.device),
                },
            }

        except Exception as e:
            import traceback
            return {"status": "error", "message": str(e), "trace": traceback.format_exc()}

    def process_predictions(self, prediction: Dict) -> Dict:
        """Legacy helper kept for backward compat."""
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
                "model_info": {"model_type": "Mask R-CNN", "device": str(self.device)}}


# Global singleton
ml_service = MLService()