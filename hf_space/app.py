"""Dental ML API — ZeroGPU Gradio Space (gr.Blocks, no api_info)."""
import os, io, base64, json
import gradio as gr
import spaces
from huggingface_hub import hf_hub_download

STAGE1_PATH = "./ml_models/maskrcnn_teeth_best.pth"
STAGE2_PATH = "./ml_models/stage2_disease_best.pth"
HF_REPO     = "ethelrani/dental-models"

DISEASE_CLASSES    = {0:"Healthy",1:"Impacted",2:"Caries",3:"Periapical Lesion",4:"Deep Caries"}
DISEASE_COLORS_BGR = {"Healthy":(100,220,0),"Impacted":(0,100,255),"Caries":(50,50,255),
                      "Deep Caries":(200,0,200),"Periapical Lesion":(0,200,255)}
DISEASE_SEVERITY   = {"Healthy":"none","Impacted":"moderate","Caries":"mild",
                      "Deep Caries":"severe","Periapical Lesion":"severe"}
DISEASE_ADVICE = {
    "Healthy":           "This tooth appears healthy. Maintain regular brushing and flossing.",
    "Impacted":          "An impacted tooth may require orthodontic or surgical evaluation.",
    "Caries":            "Early-stage cavity detected. A dental filling is usually sufficient.",
    "Deep Caries":       "Advanced decay detected. Root canal or crown may be needed.",
    "Periapical Lesion": "Infection at the tooth root. Prompt dental treatment strongly advised.",
}

stage1_model = None
stage2_model = None
_loaded = False


def _load_models():
    global stage1_model, stage2_model, _loaded
    if _loaded:
        return
    import torch, torchvision
    import torch.nn as nn
    from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
    from torchvision.models.detection.mask_rcnn import MaskRCNNPredictor

    os.makedirs("ml_models", exist_ok=True)
    if not os.path.exists(STAGE1_PATH):
        print("[ML] Downloading Stage 1...")
        hf_hub_download(repo_id=HF_REPO, filename="maskrcnn_teeth_best.pth", local_dir="ml_models")
    if not os.path.exists(STAGE2_PATH):
        print("[ML] Downloading Stage 2...")
        hf_hub_download(repo_id=HF_REPO, filename="stage2_disease_best.pth", local_dir="ml_models")

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
        print("[ML] Stage 1 OK")
    except Exception as e:
        print(f"[ML] Stage 1 error: {e}")

    try:
        m2 = torchvision.models.resnet34(weights=None)
        m2.fc = nn.Sequential(nn.Dropout(0.5), nn.Linear(m2.fc.in_features, 5))
        ckpt2 = torch.load(STAGE2_PATH, map_location="cpu", weights_only=False)
        state2 = ckpt2.get("model_state_dict", ckpt2) if isinstance(ckpt2, dict) else ckpt2
        m2.load_state_dict(state2, strict=False)
        m2.eval()
        stage2_model = m2
        print("[ML] Stage 2 OK")
    except Exception as e:
        print(f"[ML] Stage 2 error: {e}")

    _loaded = True


_load_models()


@spaces.GPU(duration=60)
def analyze(pil_image):
    import torch, numpy as np, cv2
    import torchvision.transforms.functional as TF
    from torchvision.ops import nms
    from torchvision import transforms as T
    from PIL import Image as PILImage

    if pil_image is None:
        return json.dumps({"status": "error", "message": "No image provided."})
    if stage1_model is None:
        return json.dumps({"status": "error", "message": "Stage 1 model not loaded."})

    device = torch.device("cuda")
    stage1_model.to(device)
    if stage2_model is not None:
        stage2_model.to(device)

    pil = pil_image.convert("RGB")
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

    mid_x, mid_y = W / 2, H / 2
    q_boxes = {1:[], 2:[], 3:[], 4:[]}
    for i, b in enumerate(boxes):
        cx, cy = (b[0]+b[2])/2, (b[1]+b[3])/2
        q = 1 if cy<=mid_y and cx>mid_x else 2 if cy<=mid_y else 3 if cx<=mid_x else 4
        q_boxes[q].append((cx, i))
    fdi_start = {1:11, 2:21, 3:31, 4:41}
    fdi_list = [0]*len(boxes)
    for q, items in q_boxes.items():
        for rank, (_, oi) in enumerate(sorted(items, key=lambda x: x[0], reverse=q in (2,3))):
            fdi_list[oi] = min(fdi_start[q]+rank, fdi_start[q]+7)

    annotated = np.array(pil)[...,::-1].copy()
    cv2.line(annotated,(int(mid_x),0),(int(mid_x),H),(255,255,255),2)
    cv2.line(annotated,(0,int(mid_y)),(W,int(mid_y)),(255,255,255),2)
    for lbl,lx,ly in [("Q1",int(mid_x)+10,20),("Q2",10,20),
                       ("Q3",10,int(mid_y)+20),("Q4",int(mid_x)+10,int(mid_y)+20)]:
        cv2.putText(annotated,lbl,(lx,ly),cv2.FONT_HERSHEY_SIMPLEX,0.7,(255,255,255),2)

    tf = T.Compose([T.Resize((224,224)),T.ToTensor(),
                    T.Normalize([.485,.456,.406],[.229,.224,.225])])
    teeth, disease_counts = [], {}

    for box, mask, score, fdi in zip(boxes, masks, scores, fdi_list):
        x1=max(0,int(box[0])-10); y1=max(0,int(box[1])-10)
        x2=min(W,int(box[2])+10); y2=min(H,int(box[3])+10)
        crop = pil.crop((x1,y1,x2,y2))
        if stage2_model is not None and crop.width>4 and crop.height>4:
            with torch.no_grad():
                p = torch.softmax(stage2_model(tf(crop).unsqueeze(0).to(device)),1)[0].cpu().numpy()
            li = int(p.argmax())
            cls_r = {"disease":DISEASE_CLASSES[li],"confidence":round(float(p[li]),4),
                     "probabilities":{DISEASE_CLASSES[i]:round(float(v),4) for i,v in enumerate(p)}}
        else:
            cls_r = {"disease":"Unknown","confidence":0.0,"probabilities":{}}
        d = cls_r["disease"]
        col = DISEASE_COLORS_BGR.get(d,(128,128,128))
        mb = (mask[0]>0.5).astype(np.uint8)
        cl = np.zeros_like(annotated); cl[mb==1]=col
        annotated = cv2.addWeighted(annotated,1.0,cl,0.45,0)
        cv2.rectangle(annotated,(x1,y1),(x2,y2),col,2)
        cv2.putText(annotated,str(fdi) if fdi else "?",(x1+2,y1+16),cv2.FONT_HERSHEY_SIMPLEX,0.55,col,2)
        if d!="Healthy":
            cv2.circle(annotated,(x2-6,y1+6),6,(0,0,255),-1)
        disease_counts[d] = disease_counts.get(d,0)+1
        teeth.append({
            "fdi_number":fdi,"detection_confidence":round(float(score),4),
            "bounding_box":{"x1":int(box[0]),"y1":int(box[1]),"x2":int(box[2]),"y2":int(box[3])},
            "disease":d,"disease_confidence":cls_r["confidence"],
            "disease_probabilities":cls_r["probabilities"],
            "severity":DISEASE_SEVERITY.get(d,"unknown"),
            "advice":DISEASE_ADVICE.get(d,""),
        })

    total = len(teeth)
    diseased = sum(1 for t in teeth if t["disease"]!="Healthy")
    status = ("no_teeth_detected" if total==0 else "all_healthy" if diseased==0
              else "mostly_healthy" if diseased<=total*.25
              else "moderate_issues" if diseased<=total*.5 else "significant_issues")

    out_pil = PILImage.fromarray(annotated[...,::-1])
    buf2 = io.BytesIO()
    out_pil.save(buf2,format="JPEG",quality=88)
    b64 = base64.b64encode(buf2.getvalue()).decode()

    return json.dumps({
        "status":"success",
        "summary":{"total_teeth_detected":total,"healthy_teeth":total-diseased,
                   "diseased_teeth":diseased,"overall_status":status,
                   "disease_breakdown":disease_counts},
        "teeth":teeth,
        "annotated_image_base64":b64,
    }, indent=2)


# gr.Blocks instead of gr.Interface — avoids get_api_info() schema bug entirely
with gr.Blocks(title="Dental X-ray Analysis") as demo:
    gr.Markdown("## \U0001f9b7 Dental X-ray Analysis\n"
                "**Stage 1** \u2014 Mask R-CNN: detects teeth, assigns FDI numbers.\n"
                "**Stage 2** \u2014 ResNet-34: Healthy / Caries / Deep Caries / Impacted / Periapical Lesion.")
    with gr.Row():
        img_in  = gr.Image(type="pil", label="Upload X-ray")
        txt_out = gr.Textbox(label="JSON Result", lines=30)
    btn = gr.Button("Analyze", variant="primary")
    btn.click(fn=analyze, inputs=img_in, outputs=txt_out)

demo.launch(share=True)
