import cv2
import glob
import os
import numpy as np
import random

def draw_synthetic_object(img, x1, y1, x2, y2, cls_id):
    """
    Overlays a photorealistic acoustic signature (gradient, ribs, texture) inside the bounding box.
    """
    w = x2 - x1
    h = y2 - y1
    if w <= 4 or h <= 4: return img
    
    is_horizontal = w > h
    roi = img[y1:y2, x1:x2].copy()
    
    obj_mask = np.zeros((h, w), dtype=np.float32)
    shadow_mask = np.zeros((h, w), dtype=np.float32)
    
    # Pipe (Class 2) is very thin. Cylinder (Class 3) is fatter.
    thickness = int(min(w, h) * (0.2 if cls_id == 2 else 0.4))
    thickness = max(thickness, 3)
    
    # Calculate dynamic color tint based on the image's overall hue (e.g., copper for pipes)
    avg_color = np.array(cv2.mean(roi)[:3])
    if np.sum(avg_color) < 30:
        avg_color = np.array([15, 45, 100])
    color_norm = avg_color / (np.max(avg_color) + 1e-5)
    
    # 1. Generate the curved gradient (cosine wave to simulate cylindrical reflection)
    if is_horizontal:
        # Place object near the top (assuming sonar from top)
        obj_center = thickness // 2
        y_indices = np.arange(h)
        dist_from_center = np.abs(y_indices - obj_center)
        profile = np.clip(1.0 - (dist_from_center / (thickness/2.0)), 0, 1)
        profile = np.power(profile, 0.5) 
        gradient2d = np.tile(profile, (w, 1)).T
        
        if cls_id == 3: # Cylinder/Barrel
            band_mask = np.zeros((h, w), dtype=np.float32)
            band_mask[:, int(w*0.2):int(w*0.25)] = 0.5
            band_mask[:, int(w*0.75):int(w*0.8)] = 0.5
            gradient2d += band_mask
            
        obj_mask = np.clip(gradient2d, 0, 1.0)
        
        # Draw long shadow starting immediately after the object and filling the rest of the bounding box
        shadow_start = thickness
        cv2.rectangle(shadow_mask, (0, shadow_start), (w, h), 1.0, -1)
        
    else:
        # Place object near the left (assuming sonar from left)
        obj_center = thickness // 2
        x_indices = np.arange(w)
        dist_from_center = np.abs(x_indices - obj_center)
        profile = np.clip(1.0 - (dist_from_center / (thickness/2.0)), 0, 1)
        profile = np.power(profile, 0.5)
        gradient2d = np.tile(profile, (h, 1))
        
        if cls_id == 3: # Cylinder/Barrel
            band_mask = np.zeros((h, w), dtype=np.float32)
            band_mask[int(h*0.2):int(h*0.25), :] = 0.5
            band_mask[int(h*0.75):int(h*0.8), :] = 0.5
            gradient2d += band_mask
            
        obj_mask = np.clip(gradient2d, 0, 1.0)
        
        # Draw long shadow starting immediately after the object and filling the rest of the bounding box
        shadow_start = thickness
        cv2.rectangle(shadow_mask, (shadow_start, 0), (w, h), 1.0, -1)

    noise = np.random.normal(0, 0.2, (h, w)).astype(np.float32)
    obj_mask = np.clip(obj_mask + noise * obj_mask, 0, 1.0)
    shadow_mask = cv2.GaussianBlur(shadow_mask, (5, 5), 0)
    
    roi_float = roi.astype(np.float32)
    
    # 1. Heavily darken shadow area (multiply by 0.1 for 90% opacity shadow)
    roi_float = roi_float * (1.0 - shadow_mask[:,:,np.newaxis] * 0.9)
    
    # 2. Add color-graded highlight area
    # Max brightness of highlight is 220, tinted by the image's dominant color
    highlight_3c = np.zeros_like(roi_float)
    highlight_3c[:,:,0] = obj_mask * 220.0 * color_norm[0]
    highlight_3c[:,:,1] = obj_mask * 220.0 * color_norm[1]
    highlight_3c[:,:,2] = obj_mask * 220.0 * color_norm[2]
    
    blended = np.clip(roi_float + highlight_3c, 0, 255).astype(np.uint8)
    
    img[y1:y2, x1:x2] = blended
    return img

def enhance_dataset(dataset_dir):
    labels = glob.glob(os.path.join(dataset_dir, "labels/train/*.txt"))
    count = 0
    for label_path in labels:
        # Only process subpipe and uatd
        base_name = os.path.basename(label_path)
        if not (base_name.startswith("subpipe_") or base_name.startswith("uatd_")):
            continue
            
        img_path = label_path.replace("labels", "images").replace(".txt", ".jpg")
        if not os.path.exists(img_path): continue
        
        img = cv2.imread(img_path)
        if img is None: continue
        
        H, W, _ = img.shape
        modified = False
        
        with open(label_path, "r") as f:
            lines = f.readlines()
            
        for line in lines:
            parts = line.strip().split()
            if not parts: continue
            cls_id = int(parts[0])
            
            # 2 = Pipe, 3 = Cylinder
            if cls_id in [2, 3]:
                cx, cy, bw, bh = map(float, parts[1:5])
                x1 = int((cx - bw/2) * W)
                y1 = int((cy - bh/2) * H)
                x2 = int((cx + bw/2) * W)
                y2 = int((cy + bh/2) * H)
                
                # Clip to image bounds
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(W, x2), min(H, y2)
                
                img = draw_synthetic_object(img, x1, y1, x2, y2, cls_id)
                modified = True
                
        if modified:
            cv2.imwrite(img_path, img)
            count += 1
            
    print(f"Successfully synthesized crisp pipes/cylinders into {count} images in-place!")

if __name__ == "__main__":
    enhance_dataset("Ultimate_Marine_Dataset")
