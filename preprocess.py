import cv2
import numpy as np
import os
from scipy.ndimage import uniform_filter

def gentle_median_filter(img, ksize=3):
    """
    Applies a very gentle median filter.
    Median filters are excellent for salt-and-pepper/speckle noise without blurring edges.
    """
    return cv2.medianBlur(img, ksize)

def slant_range_correction(img, sensor_altitude_pixels=30):
    """
    Converts slant-range distance to ground-range distance using cv2.remap.
    This guarantees mathematically perfect interpolation with ZERO black lines or gaps.
    """
    h, w = img.shape[:2]
    center_idx = w / 2.0
    
    # Create meshgrid of output coordinates (ground range)
    map_x = np.zeros((h, w), dtype=np.float32)
    map_y = np.zeros((h, w), dtype=np.float32)
    
    # For every y, the x mapping is the same, so we compute 1D first
    x_coords = np.arange(w, dtype=np.float32)
    ground_ranges = np.abs(x_coords - center_idx)
    
    # Slant range = sqrt(Ground Range^2 + Altitude^2)
    slant_ranges = np.sqrt(ground_ranges**2 + sensor_altitude_pixels**2)
    
    # Map back to original image coordinates
    orig_x = np.where(x_coords < center_idx, center_idx - slant_ranges, center_idx + slant_ranges)
    
    # Fill the remap matrices
    map_x[:] = orig_x
    for i in range(h):
        map_y[i, :] = i
        
    # Use BORDER_REPLICATE so the extreme edges don't turn black
    corrected_img = cv2.remap(img, map_x, map_y, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    return corrected_img

def mask_nadir(img, nadir_width_pixels=60):
    """
    Removes the blind nadir zone (dark water column).
    Instead of leaving an ugly black line, it uses OpenCV Inpainting to smoothly
    blend the surrounding seafloor over the gap, IF a gap is detected.
    """
    h, w = img.shape[:2]
    center_idx = w // 2
    
    start_col = max(0, center_idx - (nadir_width_pixels // 2))
    end_col = min(w, center_idx + (nadir_width_pixels // 2))
    
    # Check if the center is actually dark (a real nadir zone)
    center_mean = np.mean(img[:, start_col:end_col])
    overall_mean = np.mean(img)
    
    if center_mean < overall_mean * 0.7:
        # Create a mask of the exact area to inpaint
        mask = np.zeros((h, w), dtype=np.uint8)
        mask[:, start_col:end_col] = 255
        
        # Telea Inpainting algorithm smoothly fills the dark band using surrounding pixels
        inpainted_img = cv2.inpaint(img, mask, 3, cv2.INPAINT_TELEA)
        return inpainted_img
        
    return img

def normalize_sonar(img):
    """
    Normalizes the image to 0-255 using Percentile scaling (1st and 99th percentiles)
    This prevents extreme white/black speckle outliers from crushing the contrast,
    which keeps the image clear.
    """
    p_min = np.percentile(img, 1)
    p_max = np.percentile(img, 99)
    
    if p_max - p_min == 0:
        return img
        
    normalized = np.clip((img - p_min) / (p_max - p_min), 0, 1) * 255.0
    return normalized.astype(np.uint8)

def preprocess_pipeline(image_path, output_path=None):
    """
    Executes the full Phase 2 preprocessing pipeline.
    """
    print(f"Loading {image_path}...")
    img = cv2.imread(image_path)
    
    if img is None:
        raise ValueError("Image could not be loaded. Check path.")
        
    # 1. Gentle Speckle Denoise
    # Switching to a very mild median blur to preserve clarity and thin net structures
    print("Applying Gentle Median Filter...")
    denoised = gentle_median_filter(img, ksize=3)
    
    # 2. Nadir Masking
    print("Masking Nadir zone...")
    nadir_masked = mask_nadir(denoised, nadir_width_pixels=60)
    
    # 3. Slant-Range Correction
    print("Applying Slant-Range correction...")
    slant_corrected = slant_range_correction(nadir_masked, sensor_altitude_pixels=30)
    
    # 4. Normalization (Contrast enhancement)
    print("Normalizing contrast using percentile clipping...")
    final_img = normalize_sonar(slant_corrected)
    
    if output_path:
        cv2.imwrite(output_path, final_img)
        print(f"Preprocessed image saved to {output_path}")
        
    return final_img

if __name__ == "__main__":
    # Test the pipeline on our sample image
    test_img_path = "SCTD/SCTD/JPEGImages/000002.jpg"
    out_path = "preprocessed_000002.jpg"
    
    if os.path.exists(test_img_path):
        preprocess_pipeline(test_img_path, out_path)
        print("Phase 2 pipeline test successful!")
    else:
        print(f"Could not find test image: {test_img_path}")
