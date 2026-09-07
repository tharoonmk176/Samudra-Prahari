import cv2
import numpy as np
import os

def create_dummy_strips(source_img_path, output_dir="dummy_strips"):
    """Cuts a large sonar image into overlapping strips to simulate towfish movement."""
    os.makedirs(output_dir, exist_ok=True)
    img = cv2.imread(source_img_path)
    if img is None:
        print("Failed to load source image.")
        return []
        
    H, W = img.shape[:2]
    
    # Let's say the towfish moves vertically, so we have horizontal strips that overlap vertically
    num_strips = 5
    overlap = 0.3 # 30% overlap
    
    strip_h = int(H / (num_strips - (num_strips - 1) * overlap))
    step = int(strip_h * (1.0 - overlap))
    
    paths = []
    for i in range(num_strips):
        y1 = i * step
        y2 = min(H, y1 + strip_h)
        if y2 - y1 < 10: break
        
        strip = img[y1:y2, :]
        p = os.path.join(output_dir, f"strip_{i:02d}.jpg")
        cv2.imwrite(p, strip)
        paths.append(p)
        
    print(f"Created {len(paths)} overlapping dummy strips.")
    return paths

def stitch_acoustic_strip(image_paths, output_path="mosaic.jpg"):
    print(f"Attempting custom Sonar Phase-Correlation stitch on {len(image_paths)} images...")
    
    if not image_paths: return
    
    base_img = cv2.imread(image_paths[0])
    current_gray = cv2.cvtColor(base_img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    canvas = base_img.copy()
    
    for i in range(1, len(image_paths)):
        next_img = cv2.imread(image_paths[i])
        gray_next = cv2.cvtColor(next_img, cv2.COLOR_BGR2GRAY).astype(np.float32)
        
        # cv2.phaseCorrelate is mathematically perfect for sonar translation
        (dx, dy), response = cv2.phaseCorrelate(current_gray, gray_next)
        print(f"Strip {i} -> dx: {dx:.2f}, dy: {dy:.2f} (Confidence: {response:.2f})")
        
        # Calculate exactly how many pixels we moved
        shift_y = int(round(abs(dy)))
        shift_x = int(round(dx))
        
        H, W = canvas.shape[:2]
        H_next, W_next = next_img.shape[:2]
        
        # Expand the canvas downwards to make room for the new strip
        new_canvas = np.zeros((H + shift_y, W, 3), dtype=np.uint8)
        
        # Paste the existing mosaic
        new_canvas[:H, :W] = canvas
        
        # Paste the new strip, perfectly overlapping the bottom
        start_y = H - (H_next - shift_y)
        
        # Simple Alpha Blending to hide the seams
        overlap_h = H - start_y
        
        for y in range(H_next):
            if start_y + y < H:
                # We are in the overlap region! Blend it.
                alpha = y / overlap_h
                new_canvas[start_y + y, :] = cv2.addWeighted(canvas[start_y + y, :], 1 - alpha, next_img[y, :], alpha, 0)
            else:
                # Pure new image
                new_canvas[start_y + y, :] = next_img[y, :]
                
        canvas = new_canvas
        current_gray = gray_next
        
    cv2.imwrite(output_path, canvas)
    print(f"Stitching successful! Saved acoustic map to {output_path}")

if __name__ == "__main__":
    import glob
    # Find a nice long UATD image
    imgs = glob.glob("Ultimate_Marine_Dataset/images/train/pure_synth_uatd_*.jpg")
    if not imgs:
        print("No images found to test.")
    else:
        paths = create_dummy_strips(imgs[0])
        stitch_acoustic_strip(paths, "stitched_mosaic.jpg")
