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
    
    # Calculate native high-resolution image size for YOLO (must be multiple of 32)
    max_dim = max(H, W)
    native_imgsz = int(np.ceil(max_dim / 32.0)) * 32
    
    print(f"Running Native High-Res YOLOv8 Inference at {native_imgsz}px...")
    # By passing the entire massive stitched map at native resolution, we completely avoid
    # the sliding-window artifact that cuts objects in half and drops large boxes.
    results = model(mosaic, imgsz=native_imgsz, conf=0.15, iou=0.4, verbose=False)
    
    final_boxes = []
    for r in results:
        for box in r.boxes:
            conf = float(box.conf[0])
            cls_id = int(box.cls[0])
            bx1, by1, bx2, by2 = map(int, box.xyxy[0])
            
            # --- CLASSICAL CV SHADOW FILTER ---
            # Only apply strict shadow filtering to small objects (Pipes, Cylinders, Ghost Nets)
            if cls_id in [2, 3, 4]:
                roi = mosaic[by1:by2, bx1:bx2]
                if roi.shape[0] > 5 and roi.shape[1] > 5:
                    gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                    shadow_pixels = np.sum(gray_roi < 30)
                    total_pixels = roi.shape[0] * roi.shape[1]
                    shadow_ratio = shadow_pixels / total_pixels
                    
                    if shadow_ratio < 0.02:
                        conf -= 0.1 
                    elif shadow_ratio > 0.80:
                        continue 
            
            if conf >= 0.10:
                final_boxes.append((bx1, by1, bx2, by2, conf, cls_id))
                
    # Aggressive Spatial Merging (Bounding Box Union)
    # If the model outputs multiple small boxes for one shipwreck, this forces them 
    # to merge into one massive box by taking the min/max coordinates of the cluster.
    merged_boxes = []
    distance_threshold = 150 # Merge boxes that are within 150 pixels of each other
    
    # Run multiple passes to agglomerate clusters that bridge together
    for _ in range(3):
        new_merged = []
        for b in final_boxes:
            x1, y1, x2, y2, conf, cls_id = b
            
            merged = False
            for i, mb in enumerate(new_merged):
                mx1, my1, mx2, my2, mconf, mcls_id = mb
                if cls_id != mcls_id: continue
                
                # Check distance/overlap
                ex1, ey1, ex2, ey2 = x1 - distance_threshold, y1 - distance_threshold, x2 + distance_threshold, y2 + distance_threshold
                emx1, emy1, emx2, emy2 = mx1 - distance_threshold, my1 - distance_threshold, mx2 + distance_threshold, my2 + distance_threshold
                
                if not (ex2 < emx1 or ex1 > emx2 or ey2 < emy1 or ey1 > emy2):
                    # Intersects! Take the UNION of the coordinates
                    new_x1 = min(x1, mx1)
                    new_y1 = min(y1, my1)
                    new_x2 = max(x2, mx2)
                    new_y2 = max(y2, my2)
                    new_conf = max(conf, mconf) # Keep highest confidence
                    
                    new_merged[i] = (new_x1, new_y1, new_x2, new_y2, new_conf, cls_id)
                    merged = True
                    break
                    
            if not merged:
                new_merged.append(b)
        final_boxes = new_merged
            
    # Draw boxes
    colors = {
        0: (0, 0, 255),    # Shipwreck: Red
        1: (255, 0, 0),    # Aircraft: Blue
        2: (0, 255, 255),  # Pipe: Yellow
        3: (255, 165, 0),  # Cylinder: Orange
        4: (0, 255, 0)     # Ghost Net: Green
    }
    
    names = ['Shipwreck', 'Aircraft', 'Pipe', 'Cylinder', 'Ghost Net']
    
    print(f"Found {len(final_boxes)} debris items in the acoustic map!")
    
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
