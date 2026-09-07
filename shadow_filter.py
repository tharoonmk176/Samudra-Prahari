import cv2
import numpy as np
import os
from ultralytics import YOLO

def analyze_shadow(crop_img, cls_name="unknown"):
    """
    Analyzes the acoustic shadow geometry in a bounding box crop.
    """
    if len(crop_img.shape) == 3:
        gray = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)
    else:
        gray = crop_img
        
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        return 0.3
        
    largest_contour = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(largest_contour)
    if area < 20: return 0.5
        
    hull = cv2.convexHull(largest_contour)
    hull_area = cv2.contourArea(hull)
    if hull_area == 0: return 0.5
        
    solidity = area / hull_area
    perimeter = cv2.arcLength(largest_contour, True)
    complexity = (perimeter ** 2) / (area + 1e-5)
    
    confidence_multiplier = 1.0
    
    # Ghost Nets cast highly chaotic, porous shadows
    if cls_name == "ghost_net":
        if complexity > 30 or solidity < 0.70:
            confidence_multiplier = 1.2 # Boost: It looks properly chaotic!
        else:
            confidence_multiplier = 0.8 # Penalty: It looks too solid for a net
    # Rigid Objects (Ships, Pipes, Cylinders) cast regular geometric shadows
    else:
        if solidity < 0.65 or complexity > 40:
            confidence_multiplier = 0.4 # Highly jagged (Rocks)
        elif solidity > 0.85:
            confidence_multiplier = 1.1 # Very regular (Man-made)
            
    return min(1.0, max(0.1, confidence_multiplier))

def run_phase3(img_path, model_path="models/GhostNetSonar/best.onnx", out_path="outputs/phase3_output.jpg", conf_thresh=0.15):
    """
    Executes the Detection + Shadow Filter pipeline.
    """
    print(f"Loading image {img_path}...")
    img = cv2.imread(img_path)
    if img is None:
        raise ValueError("Could not load image.")
        
    print("Running YOLOv8 Object Detection...")
    model = YOLO(model_path)
    results = model(img, conf=conf_thresh)
    
    final_detections = []
    
    for r in results:
        for box in r.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cls_id = int(box.cls[0])
            raw_conf = float(box.conf[0])
            cls_name = r.names[cls_id]
            
            # Extract the bounding box crop
            crop = img[y1:y2, x1:x2]
            
            # Ensure crop is valid
            if crop.size == 0:
                continue
                
            # Class-specific geometric validation (Pipe & Cylinder)
            box_w = x2 - x1
            box_h = y2 - y1
            aspect_ratio = max(box_w, box_h) / (min(box_w, box_h) + 1e-5)
            
            geometric_penalty = 1.0
            if cls_name in ["pipe", "cylinder"]:
                # Many real labeled pipes/cylinders are small and roughly square. 
                # Relaxing this threshold from 1.5 to 1.15 prevents penalizing real targets.
                if aspect_ratio < 1.15:
                    print(f"-> GEOMETRY WARNING: {cls_name} lacks elongated aspect ratio ({aspect_ratio:.2f}). Penalizing.")
                    geometric_penalty = 0.6
                else:
                    # Good elongated shape
                    geometric_penalty = 1.3

            # Run the Classical CV Shadow Filter
            shadow_multiplier = analyze_shadow(crop, cls_name=cls_name)
            
            # Recalibrate confidence combining shadow and geometric logic
            new_conf = raw_conf * shadow_multiplier * geometric_penalty
            
            # Filter out false positives (e.g., if new confidence drops below 25%)
            if new_conf >= 0.25:
                final_detections.append({
                    "class": cls_name,
                    "box": (x1, y1, x2, y2),
                    "raw_conf": raw_conf,
                    "calibrated_conf": new_conf,
                    "multiplier": shadow_multiplier
                })
                
                # Draw the bounding box and calibrated confidence on the image for visualization
                color = (0, 255, 0) if shadow_multiplier >= 1.0 else (0, 165, 255) # Green for good, Orange for penalized
                cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
                label = f"{cls_name}: {new_conf:.2f} (raw: {raw_conf:.2f})"
                
                # Prevent text from being cut off at the top of the image
                y_label = y1 - 10 if y1 - 10 > 15 else y1 + 20
                cv2.putText(img, label, (x1, y_label), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            else:
                print(f"-> REJECTED FALSE POSITIVE: {cls_name} (Raw Conf: {raw_conf:.2f} dropped to {new_conf:.2f} due to jagged shadow)")
                
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    cv2.imwrite(out_path, img)
    print(f"\nPhase 3 complete! Kept {len(final_detections)} valid detections. Saved visualization to {out_path}")
    
    return final_detections

if __name__ == "__main__":
    # Test Phase 3 using the preprocessed image from Phase 2
    test_img = "preprocessed_000002.jpg"
    if os.path.exists(test_img):
        run_phase3(test_img)
    else:
        print(f"Error: {test_img} not found. Please run Phase 2 first.")
