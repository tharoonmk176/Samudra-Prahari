import cv2
import streamlit as st
from src.config import CLASS_NAMES, CLASS_COLORS_CV
from src.processing.preprocess import (
    gentle_median_filter, mask_nadir, slant_range_correction, normalize_sonar
)
from src.processing.shadow_filter import shadow_score, recalibrate

@st.cache_resource
def load_model(weights_path):
    from ultralytics import YOLO
    return YOLO(weights_path)

def process_single_image(img, model, enable_denoise, enable_nadir, enable_slant,
                         nadir_side="left", conf_thresh=0.15, keep_thresh=0.25):
    if enable_denoise:
        img = gentle_median_filter(img)
    if enable_nadir:
        img = mask_nadir(img)
    if enable_slant:
        img = slant_range_correction(img)

    img = normalize_sonar(img)

    # Completely removed SAHI because YOLO was trained on squashed whole images!
    # Ultralytics natively handles squashing to 640x640 and upscaling the boxes back.
    results = model(img, conf=conf_thresh, iou=keep_thresh, verbose=False)
    
    boxes_tuples = []
    detections = []
    
    for r in results:
        for box in r.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf = float(box.conf[0])
            cls_id = int(box.cls[0])
            
            # Filter out tiny boxes
            if (x2 - x1) < 15 and (y2 - y1) < 15:
                continue
                
            boxes_tuples.append((x1, y1, x2, y2, conf, cls_id))
            
            cls_name = model.names[cls_id] if hasattr(model, 'names') else str(cls_id)
            
            # Calculate Physical Shadow Score to verify if it's a real 3D object or just sand noise!
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
            score, dbg = shadow_score(gray, [x1, y1, x2, y2], nadir_side, cls_name=cls_name)
            
            # Recalibrate YOLO confidence based on the physical acoustic shadow presence
            calibrated_conf = recalibrate(conf, score)
            
            detections.append({
                "class": cls_name,
                "confidence": calibrated_conf,  # Expose the recalibrated confidence to the UI
                "raw_conf": conf,
                "shadow_score": round(score, 3),
                "box": [x1, y1, x2, y2]
            })

    return img, detections, boxes_tuples


def draw_detections(img, boxes_tuples):
    vis = img.copy()
    for b in boxes_tuples:
        x1, y1, x2, y2, conf, cls_id = b
        # Ensure coordinates are within image bounds to prevent OpenCV drawing errors on edges
        h, w = img.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        
        color = CLASS_COLORS_CV.get(cls_id, (255, 255, 255))
        cls_name = CLASS_NAMES[cls_id] if cls_id < len(CLASS_NAMES) else f"cls_{cls_id}"

        # HUD Style Bounding Box (Matching React SVG)
        thickness = 2
        line_length = 15
        
        # Inner translucent fill
        overlay = vis.copy()
        cv2.rectangle(overlay, (x1, y1), (x2, y2), color, cv2.FILLED)
        cv2.addWeighted(overlay, 0.05, vis, 0.95, 0, vis)
        
        # Thin full box
        cv2.rectangle(vis, (x1, y1), (x2, y2), color, thickness)
        
        # Corner Brackets (matching strokeColor in SVG)
        bracket_thick = 2
        # Top Left
        cv2.line(vis, (x1, y1), (x1 + line_length, y1), color, bracket_thick)
        cv2.line(vis, (x1, y1), (x1, y1 + line_length), color, bracket_thick)
        # Top Right
        cv2.line(vis, (x2, y1), (x2 - line_length, y1), color, bracket_thick)
        cv2.line(vis, (x2, y1), (x2, y1 + line_length), color, bracket_thick)
        # Bottom Left
        cv2.line(vis, (x1, y2), (x1 + line_length, y2), color, bracket_thick)
        cv2.line(vis, (x1, y2), (x1, y2 - line_length), color, bracket_thick)
        # Bottom Right
        cv2.line(vis, (x2, y2), (x2 - line_length, y2), color, bracket_thick)
        cv2.line(vis, (x2, y2), (x2, y2 - line_length), color, bracket_thick)
        
    return vis
