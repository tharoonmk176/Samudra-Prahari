import cv2
import numpy as np
import os
import random
import math

def draw_trawl_net(layer, start_x, start_y, net_length):
    """Draws a conical trawl net (wide mouth, tapering to a point)."""
    angle = random.uniform(0, 2 * math.pi)
    end_x = start_x + int(net_length * math.cos(angle))
    end_y = start_y + int(net_length * math.sin(angle))
    
    mouth_width = random.randint(40, 80)
    num_rings = random.randint(8, 15)
    
    # Draw longitudinal support ropes
    num_supports = 6
    for i in range(num_supports):
        # Calculate mouth points
        mouth_angle = angle + math.pi/2 + (i / num_supports) * math.pi - math.pi/2
        mx = start_x + int(mouth_width * math.cos(mouth_angle))
        my = start_y + int(mouth_width * math.sin(mouth_angle))
        cv2.line(layer, (mx, my), (end_x, end_y), 25.0, 1)
        
    # Draw tapering rings
    for i in range(num_rings):
        t = i / num_rings
        cx = int(start_x + t * (end_x - start_x))
        cy = int(start_y + t * (end_y - start_y))
        radius = int(mouth_width * (1.0 - t))
        # Draw ring as an ellipse angled towards the end
        axes = (radius, max(2, int(radius * 0.3)))
        cv2.ellipse(layer, (cx, cy), axes, math.degrees(angle), 0, 360, 25.0, 1)
        
    return min(start_x, end_x) - mouth_width, min(start_y, end_y) - mouth_width, abs(end_x - start_x) + mouth_width*2, abs(end_y - start_y) + mouth_width*2

def draw_gillnet(layer, start_x, start_y, net_length):
    """Draws a long, snaking gillnet ribbon."""
    pts = []
    curr_x, curr_y = start_x, start_y
    pts.append((curr_x, curr_y))
    
    num_segments = random.randint(4, 8)
    segment_len = net_length // num_segments
    angle = random.uniform(0, 2 * math.pi)
    
    for _ in range(num_segments):
        # Slightly alter angle to make it snake
        angle += random.uniform(-0.8, 0.8)
        curr_x += int(segment_len * math.cos(angle))
        curr_y += int(segment_len * math.sin(angle))
        pts.append((curr_x, curr_y))
        
    # Interpolate points for a smooth curve
    curve_pts = []
    for i in range(len(pts)-1):
        x1, y1 = pts[i]
        x2, y2 = pts[i+1]
        for t in np.linspace(0, 1, 10):
            cx = int(x1 + t*(x2-x1))
            cy = int(y1 + t*(y2-y1))
            curve_pts.append((cx, cy))
            
    # Draw the net mesh along the spine
    net_width = random.randint(20, 40)
    for i in range(0, len(curve_pts), 3): # Spacing
        cx, cy = curve_pts[i]
        # Tangent angle
        if i < len(curve_pts)-1:
            nx, ny = curve_pts[i+1]
            tangent = math.atan2(ny - cy, nx - cx)
        else:
            tangent = 0
            
        perp = tangent + math.pi/2
        px1 = cx + int(net_width * math.cos(perp))
        py1 = cy + int(net_width * math.sin(perp))
        px2 = cx - int(net_width * math.cos(perp))
        py2 = cy - int(net_width * math.sin(perp))
        
        cv2.line(layer, (px1, py1), (px2, py2), 25.0, 1)
        
    # Draw outer bounding ropes
    for i in range(len(curve_pts)-1):
        cx1, cy1 = curve_pts[i]
        cx2, cy2 = curve_pts[i+1]
        cv2.line(layer, (cx1, cy1), (cx2, cy2), 25.0, 1) # Center spine
        
    all_x = [p[0] for p in curve_pts]
    all_y = [p[1] for p in curve_pts]
    return min(all_x) - net_width, min(all_y) - net_width, max(all_x) - min(all_x) + net_width*2, max(all_y) - min(all_y) + net_width*2

def create_synthetic_net_physics(img_shape=(640, 640), sensor_alt=150.0):
    H, W = img_shape
    center_x = W // 2
    
    # 1. Initialize 2.5D Heightmap (Z-axis) - Pure Grayscale
    Z = np.random.normal(0, 1, (H, W)).astype(np.float32)
    Z = cv2.GaussianBlur(Z, (15, 15), 0) * 5.0
    
    # Add random rocks/boulders to the seafloor
    num_rocks = random.randint(3, 10)
    for _ in range(num_rocks):
        rx = random.randint(50, W-50)
        ry = random.randint(50, H-50)
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
    
    # 2. Draw Realistic Human Fishing Nets
    net_layer = np.zeros((H, W), dtype=np.float32)
    
    net_length = random.randint(100, 250)
    
    # Spawn outside nadir
    if random.choice([True, False]):
        max_x = max(50, center_x - 30 - net_length)
        start_x = random.randint(50, max_x)
    else:
        start_x = random.randint(center_x + 30, W - net_length - 30)
        
    start_y = random.randint(net_length, H - net_length)
    
    # Randomly choose between Trawl Net (Cone) or Gillnet (Snaking Ribbon)
    if random.choice([True, False]):
        bx, by, bw, bh = draw_trawl_net(net_layer, start_x, start_y, net_length)
    else:
        bx, by, bw, bh = draw_gillnet(net_layer, start_x, start_y, net_length)
        
    # Elastic Tangling (Currents folding the net)
    Y_idx, X_idx = np.indices((H, W))
    freq_x, freq_y = random.uniform(8.0, 20.0), random.uniform(8.0, 20.0)
    amp_x, amp_y = random.uniform(5.0, 15.0), random.uniform(5.0, 15.0)
    
    map_x = (X_idx + amp_x * np.sin(Y_idx / freq_x)).astype(np.float32)
    map_y = (Y_idx + amp_y * np.cos(X_idx / freq_y)).astype(np.float32)
            
    net_layer = cv2.remap(net_layer, map_x, map_y, interpolation=cv2.INTER_LINEAR)
    
    Z += net_layer
    
    # 3. Ray-Casted Acoustic Shadows (1D Ray Marching)
    X_dist = np.abs(X_idx - center_x).astype(np.float32) + 1e-5
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
    
    # 4. Lambertian Acoustic Scattering
    dZ_dY, dZ_dX = np.gradient(Z)
    
    Ray_X = center_x - X_idx
    Ray_Z = sensor_alt - Z
    
    len_Ray = np.sqrt(Ray_X**2 + Ray_Z**2)
    Ray_X_n = Ray_X / len_Ray
    Ray_Z_n = Ray_Z / len_Ray
    
    len_N = np.sqrt(dZ_dX**2 + dZ_dY**2 + 1.0)
    N_X = -dZ_dX / len_N
    N_Z = 1.0 / len_N
    
    intensity = (N_X * Ray_X_n + N_Z * Ray_Z_n)
    intensity = np.clip(intensity, 0, 1)
    
    intensity = np.where(net_layer > 2, intensity ** 0.5 * 1.5, intensity)
    
    # 5. Rayleigh Speckle Noise & TVG Attenuation (Pure Black and White)
    speckle = np.random.rayleigh(scale=1.0, size=(H, W)).astype(np.float32)
    
    final_img = 100 * intensity * shadow_mask * speckle
    
    nadir_width = 40
    for x in range(W):
        dist = abs(x - center_x)
        if dist < nadir_width:
            final_img[:, x] *= (dist / nadir_width) ** 2
        elif dist > center_x * 0.5:
            final_img[:, x] *= 1.0 - ((dist - center_x * 0.5) / (center_x * 0.5)) * 0.4
            
    final_img = np.clip(final_img, 0, 255).astype(np.uint8)
    # Ensure it is purely Black and White / Grayscale format
    final_img = cv2.cvtColor(final_img, cv2.COLOR_GRAY2BGR)
    
    # Bounding Box (Clamp coordinates to 0-1)
    box_w = min(1.0, max(0.01, bw / W))
    box_h = min(1.0, max(0.01, bh / H))
    box_cx = min(1.0, max(0.0, (bx + bw / 2.0) / W))
    box_cy = min(1.0, max(0.0, (by + bh / 2.0) / H))
    
    yolo_label = f"3 {box_cx:.6f} {box_cy:.6f} {box_w:.6f} {box_h:.6f}"
    
    return final_img, yolo_label

def generate_dataset(num_images=10, output_dir="synthetic_nets"):
    os.makedirs(os.path.join(output_dir, "images"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "labels"), exist_ok=True)
    
    print(f"Generating {num_images} real-world shaped fishing nets (pure grayscale)...")
    for i in range(num_images):
        img, label = create_synthetic_net_physics()
        cv2.imwrite(os.path.join(output_dir, "images", f"synth_net_{i:04d}.jpg"), img)
        with open(os.path.join(output_dir, "labels", f"synth_net_{i:04d}.txt"), "w") as f:
            f.write(label)
            
    print(f"Generated successfully in {output_dir}/")

if __name__ == "__main__":
    generate_dataset(10)
