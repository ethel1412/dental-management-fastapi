import torch
import torchvision
from torchvision import transforms
from PIL import Image
import numpy as np
import json
from typing import Dict, List
from app.config import settings

class MLService:
    
    def __init__(self):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = None
        self.load_model()
    
    def load_model(self):
        """Load the Mask R-CNN model"""
        try:
            self.model = torch.load(settings.ML_MODEL_PATH, map_location=self.device)
            self.model.eval()
            print("ML Model loaded successfully")
        except Exception as e:
            print(f"Error loading ML model: {str(e)}")
            self.model = None
    
    def preprocess_image(self, image_path: str):
        """Preprocess image for model input"""
        image = Image.open(image_path).convert("RGB")
        transform = transforms.Compose([
            transforms.ToTensor(),
        ])
        return transform(image).unsqueeze(0).to(self.device)
    
    def analyze_xray(self, image_path: str) -> Dict:
        """Analyze dental X-ray image"""
        if self.model is None:
            return {
                "status": "error",
                "message": "ML model not loaded"
            }
        
        try:
            # Preprocess image
            image_tensor = self.preprocess_image(image_path)
            
            # Run inference
            with torch.no_grad():
                predictions = self.model(image_tensor)
            
            # Process results
            result = self.process_predictions(predictions[0])
            
            return {
                "status": "success",
                "analysis": result
            }
        
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    def process_predictions(self, prediction: Dict) -> Dict:
        """Process model predictions into readable format"""
        boxes = prediction['boxes'].cpu().numpy()
        labels = prediction['labels'].cpu().numpy()
        scores = prediction['scores'].cpu().numpy()
        masks = prediction['masks'].cpu().numpy()
        
        # Filter by confidence threshold
        threshold = 0.5
        valid_indices = scores >= threshold
        
        detected_teeth = []
        for i, (box, label, score, mask) in enumerate(zip(
            boxes[valid_indices],
            labels[valid_indices],
            scores[valid_indices],
            masks[valid_indices]
        )):
            tooth_data = {
                "tooth_id": int(label),
                "confidence": float(score),
                "bounding_box": {
                    "x1": float(box[0]),
                    "y1": float(box[1]),
                    "x2": float(box[2]),
                    "y2": float(box[3])
                },
                "mask_area": float(mask.sum())
            }
            detected_teeth.append(tooth_data)
        
        return {
            "total_teeth_detected": len(detected_teeth),
            "teeth": detected_teeth,
            "model_info": {
                "model_type": "Mask R-CNN",
                "device": str(self.device)
            }
        }

# Global instance
ml_service = MLService()
