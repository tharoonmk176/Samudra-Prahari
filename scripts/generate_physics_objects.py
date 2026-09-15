import cv2
import numpy as np
import os
import random
import math

def draw_pipe(layer, start_x, start_y, length):
    angle = random.uniform(0, 2*math.pi)
    end_x = int(start_x + length * math.cos(angle))
    end_y = int(start_y + length * math.sin(angle))
    
    thickness = random.randint(4, 10) # Very thin pipe
    
    for t in range(thickness, 0, -1):
        h_val = 40.0 * (1 - (t/thickness)**2) # Parabolic cylindrical curve
        cv2.line(layer, (start_x, start_y), (end_x, end_y), h_val, t)
        
    return min(start_x, end_x)-thickness, min(start_y, end_y)-thickness, abs(end_x-start_x)+thickness*2, abs(end_y-start_y)+thickness*2

def draw_cylinder(layer, start_x, start_y):
    length = random.randint(20, 50) # Short
    angle = random.uniform(0, 2*math.pi)
    end_x = int(start_x + length * math.cos(angle))
    end_y = int(start_y + length * math.sin(angle))
    
    thickness = random.randint(15, 30) # Fat barrel
    
    for t in range(thickness, 0, -1):
        h_val = 60.0 * (1 - (t/thickness)**2) 
        cv2.line(layer, (start_x, start_y), (end_x, end_y), h_val, t)
        
    # Barrel Ribs
    rib_width = max(2, thickness//8)
    cx1 = int(start_x + 0.2*(end_x-start_x))
    cy1 = int(start_y + 0.2*(end_y-start_y))
    cx2 = int(start_x + 0.8*(end_x-start_x))
    cy2 = int(start_y + 0.8*(end_y-start_y))
    cv2.circle(layer, (cx1, cy1), thickness//2 + 2, 70.0, rib_width)
    cv2.circle(layer, (cx2, cy2), thickness//2 + 2, 70.0, rib_width)
    
    return min(start_x, end_x)-thickness, min(start_y, end_y)-thickness, abs(end_x-start_x)+thickness*2, abs(end_y-start_y)+thickness*2

def create_synthetic_physics(cls_type, img_shape=(640, 640), sensor_alt=150.0):
    H, W = img_shape
    center_x = W // 2
    
    Z = np.random.normal(0, 1, (H, W)).astype(np.float32)
    Z = cv2.GaussianBlur(Z, (15, 15), 0) * 5.0
    
    num_rocks = random.randint(3, 10)
    for _ in range(num_rocks):
        rx = random.randint(50, W-50); ry = random.randint(50, H-50)
        rw = random.randint(10, 30)
        rock_height = random.uniform(10.0, 40.0)
        y_grid, x_grid = np.ogrid[-rw:rw, -rw:rw]
        dist_sq = x_grid**2 + y_grid**2
        mask = np.exp(-dist_sq / (2 * (rw/2)**2)) * rock_height
        
        y1, y2 = max(0, ry-rw), min(H, ry+rw)
        x1, x2 = max(0, rx-rw), min(W, rx+rw)
        my1, my2 = max(0, -(ry-rw)), rw*2 - max(0, (ry+rw)-H)
        mx1, mx2 = max(0, -(rx-rw)), rw*2 - max(0, (rx+rw)-W)
        Z[y1:y2, x1:x2] += mask[my1:my2, mx1:mx2]
    
    obj_layer = np.zeros((H, W), dtype=np.float32)
    length = random.randint(100, 200) # Restrict length so it fits on one side of the nadir
    
    if random.choice([True, False]):
        max_x = max(50, center_x - 30 - length)
        start_x = random.randint(50, max_x)
    else:
        start_x = random.randint(center_x + 30, W - length - 30)
    start_y = random.randint(length, H - length)
    
    if cls_type == 2: # Pipe
        bx, by, bw, bh = draw_pipe(obj_layer, start_x, start_y, length)
    elif cls_type == 3: # Cylinder
        bx, by, bw, bh = draw_cylinder(obj_layer, start_x, start_y)
    
    Z += obj_layer
    
    # Ray-Casted Acoustic Shadows
    X_dist = np.abs(np.indices((H, W))[1] - center_x).astype(np.float32) + 1e-5
    slope = (sensor_alt - Z) / X_dist
    
    shadow_mask = np.ones((H, W), dtype=np.float32)
    if W - center_x > 0:
        slope_right = slope[:, center_x:]
        min_slope_right = np.minimum.accumulate(slope_right, axis=1)
        shadow_mask[:, center_x:] = np.where(slope_right > min_slope_right + 0.05, 0.1, 1.0)
    if center_x > 0:
        slope_left = slope[:, :center_x][:, ::-1]
        min_slope_left = np.minimum.accumulate(slope_left, axis=1)
        shadow_mask_left = np.where(slope_left > min_slope_left + 0.05, 0.1, 1.0)
        shadow_mask[:, :center_x] = shadow_mask_left[:, ::-1]
        
    shadow_mask = cv2.blur(shadow_mask, (5, 1))
    
    # Lambertian Acoustic Scattering
    dZ_dY, dZ_dX = np.gradient(Z)
    Ray_X = center_x - np.indices((H, W))[1]
    Ray_Z = sensor_alt - Z
    len_Ray = np.sqrt(Ray_X**2 + Ray_Z**2)
    Ray_X_n, Ray_Z_n = Ray_X / len_Ray, Ray_Z / len_Ray
    len_N = np.sqrt(dZ_dX**2 + dZ_dY**2 + 1.0)
    N_X, N_Z = -dZ_dX / len_N, 1.0 / len_N
    
    intensity = np.clip(N_X * Ray_X_n + N_Z * Ray_Z_n, 0, 1)
    intensity = np.where(obj_layer > 2, intensity ** 0.5 * 1.5, intensity)
    
    speckle = np.random.rayleigh(scale=1.0, size=(H, W)).astype(np.float32)
    final_img = 100 * intensity * shadow_mask * speckle
    
    # TVG Attenuation & Nadir
    nadir_width = 40
    for x in range(W):
        dist = abs(x - center_x)
        if dist < nadir_width: final_img[:, x] *= (dist / nadir_width) ** 2
        elif dist > center_x * 0.5: final_img[:, x] *= 1.0 - ((dist - center_x * 0.5) / (center_x * 0.5)) * 0.4
            
    final_img = np.clip(final_img, 0, 255).astype(np.uint8)
    
    # Ensure it is purely Black and White / Grayscale format
    final_img = cv2.cvtColor(final_img, cv2.COLOR_GRAY2BGR)
    
    box_w = min(1.0, max(0.01, bw / W))
    box_h = min(1.0, max(0.01, bh / H))
    box_cx = min(1.0, max(0.0, (bx + bw / 2.0) / W))
    box_cy = min(1.0, max(0.0, (by + bh / 2.0) / H))
    
    yolo_label = f"{cls_type} {box_cx:.6f} {box_cy:.6f} {box_w:.6f} {box_h:.6f}"
    return final_img, yolo_label

def swap_dataset(cls_id, prefix):
    import glob
    # Delete old bad images
    old_imgs = glob.glob(f"Ultimate_Marine_Dataset/images/train/{prefix}_*.jpg")
    old_txts = glob.glob(f"Ultimate_Marine_Dataset/labels/train/{prefix}_*.txt")
    for f in old_imgs + old_txts:
        os.remove(f)
        
    print(f"Generating 300 photorealistic physics engine scenes for Class {cls_id}...")
    for i in range(300):
        img, label = create_synthetic_physics(cls_id)
        cv2.imwrite(f"Ultimate_Marine_Dataset/images/train/pure_synth_{prefix}_{i:04d}.jpg", img)
        with open(f"Ultimate_Marine_Dataset/labels/train/pure_synth_{prefix}_{i:04d}.txt", "w") as f:
            f.write(label)

if __name__ == "__main__":
    swap_dataset(2, "subpipe") # Pipe
    swap_dataset(3, "uatd")    # Cylinder
    print("Flawless Physics replacement complete!")
