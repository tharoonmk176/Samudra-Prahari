import cv2
import numpy as np
import os
import glob
from ultralytics import YOLO

def create_acoustic_map_from_strips(image_paths, direction="Vertical"):
    """Stitches images continuously based on direction."""
    print(f"Stitching {len(image_paths)} acoustic strips {direction}ly...")
    if not image_paths: return None
    
    images = []
    base_dim = None
    
    for p in image_paths:
        img = cv2.imread(p)
        if direction == "Vertical":
            if base_dim is None: base_dim = img.shape[1]
            if img.shape[1] != base_dim:
                img = cv2.resize(img, (base_dim, img.shape[0]))
        else:
            if base_dim is None: base_dim = img.shape[0]
            if img.shape[0] != base_dim:
                img = cv2.resize(img, (img.shape[1], base_dim))
                
        images.append(img)
        
    if direction == "Vertical":
        canvas = cv2.vconcat(images)
    else:
        canvas = cv2.hconcat(images)
        
    return canvas

def detect_on_acoustic_map(mosaic, model_path="models/GhostNetSonar/best.pt"):
    """Runs YOLO inference on chunks of the giant mosaic to prevent squashing/distortion."""
    print(f"Loading Ultimate YOLOv8 model from {model_path}...")
    model = YOLO(model_path)
    
    H, W = mosaic.shape[:2]
    
    # We slide a 640x640 window down the mosaic
    # Step size 320 to ensure 50% overlap (so objects aren't cut in half)
    chunk_size = 640
    step = 320
    
    boxes = [] # (x1, y1, x2, y2, conf, cls_id)
    
    for y in range(0, H, step):
        y1 = y
        y2 = min(H, y + chunk_size)
        
        if y2 - y1 < 100: break # Skip tiny slivers
        
        chunk = mosaic[y1:y2, :]
        
        # We enforce chunk_size for YOLO so it doesn't rescale
        # If it's the bottom chunk, we pad it to 640
        padded_chunk = np.zeros((chunk_size, W, 3), dtype=np.uint8)
        padded_chunk[:(y2-y1), :] = chunk
        results = model(padded_chunk, conf=0.15, iou=0.4, verbose=False)
        
        for r in results:
            for box in r.boxes:
                conf = float(box.conf[0])
                cls_id = int(box.cls[0])
                bx1, by1, bx2, by2 = map(int, box.xyxy[0])
                
                # If box is in the padded black area, ignore
                if by1 > (y2-y1): continue
                
                # --- CLASSICAL CV SHADOW FILTER ---
                # Only apply strict shadow filtering to small objects (Pipes, Cylinders, Ghost Nets)
                # Shipwrecks (cls 0) and Aircraft (cls 1) cast massive, unpredictable shadows that shouldn't be penalized
                cls_id = int(box.cls[0])
                if cls_id in [2, 3, 4]:
                    roi = chunk[by1:min(by2, y2-y1), bx1:bx2]
                    if roi.shape[0] > 5 and roi.shape[1] > 5:
                        gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                        shadow_pixels = np.sum(gray_roi < 30)
                        total_pixels = roi.shape[0] * roi.shape[1]
                        shadow_ratio = shadow_pixels / total_pixels
                        
                        if shadow_ratio < 0.02:
                            conf -= 0.1 
                        elif shadow_ratio > 0.80:
                            continue 
                
                if conf < 0.10: continue 
                
                # Convert chunk coordinates to global mosaic coordinates
                global_y1 = y1 + by1
                global_y2 = y1 + min(by2, y2-y1)
                
                boxes.append((bx1, global_y1, bx2, global_y2, conf, cls_id))
                
    # Basic Non-Maximum Suppression (NMS) to remove duplicates from overlap
    final_boxes = []
    # Very crude NMS
    for b in boxes:
        duplicate = False
        for fb in final_boxes:
            # Check center distance
            cx1, cy1 = (b[0]+b[2])/2, (b[1]+b[3])/2
            cx2, cy2 = (fb[0]+fb[2])/2, (fb[1]+fb[3])/2
            dist = np.sqrt((cx1-cx2)**2 + (cy1-cy2)**2)
            if dist < 100 and b[5] == fb[5]: # Same class and close
                duplicate = True
                break
        if not duplicate:
            final_boxes.append(b)
            
    # Draw boxes
    colors = {
        0: (0, 0, 255),    # Shipwreck: Red
        1: (255, 0, 0),    # Aircraft: Blue
        2: (0, 255, 255),  # Pipe: Yellow
        3: (255, 165, 0),  # Cylinder: Orange
        4: (0, 255, 0)     # Ghost Net: Green
    }
    
    names = ['Shipwreck', 'Aircraft', 'Pipe', 'Cylinder', 'Ghost Net']
    
    print(f"Found {len(final_boxes)} anomalies in the acoustic map!")
    
    for b in final_boxes:
        x1, y1, x2, y2, conf, cls_id = b
        color = colors.get(cls_id, (255, 255, 255))
        label = f"{names[cls_id]} {conf:.2f}"
        
        cv2.rectangle(mosaic, (x1, y1), (x2, y2), color, 3)
        cv2.putText(mosaic, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        
    return mosaic, final_boxes

if __name__ == "__main__":
    # Test on the dummy strips we created earlier
    strips = sorted(glob.glob("dummy_strips/*.jpg"))
    if not strips:
        print("Run acoustic_stitcher.py first to generate dummy strips.")
    else:
        mosaic = create_acoustic_map_from_strips(strips)
        final_map = detect_on_acoustic_map(mosaic)
        cv2.imwrite("final_anomaly_acoustic_map.jpg", final_map)
        print("Success! Saved final_anomaly_acoustic_map.jpg")
