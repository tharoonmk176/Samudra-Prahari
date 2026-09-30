import pyxtf
import numpy as np
import cv2
import os

def xtf_to_images(xtf_path, output_dir="temp_uploads"):
    """
    Parses an XTF file and extracts the Port and Starboard acoustic channels 
    into standard PNG images so they can be fed into the AI pipeline.
    """
    (file_header, packets) = pyxtf.xtf_read(xtf_path)
    
    # Filter only sonar packets
    sonar_packets = packets[pyxtf.XTFHeaderType.sonar]
    
    # Assuming channels 0 and 1 are Port and Starboard
    # XTF format can be complex, we will concatenate the pings
    
    if not sonar_packets:
        raise ValueError("No sonar packets found in the XTF file.")
    
    port_data = []
    stbd_data = []
    
    for packet in sonar_packets:
        # Each packet contains multiple channels
        # Usually channel 0 is port, 1 is starboard
        if len(packet.data) > 0:
            port_data.append(packet.data[0])
        if len(packet.data) > 1:
            stbd_data.append(packet.data[1])
            
    port_img = np.array(port_data, dtype=np.float32) if port_data else None
    stbd_img = np.array(stbd_data, dtype=np.float32) if stbd_data else None
    
    generated_images = []
    
    base_name = os.path.basename(xtf_path).replace('.xtf', '')
    
    # Normalize to 0-255 uint8 and equalize
    for img_data, side in [(port_img, "port"), (stbd_img, "stbd")]:
        if img_data is not None and img_data.size > 0:
            img_data = np.clip(img_data, 0, None) # Remove negatives
            # Normalize to 0-255
            if np.max(img_data) > 0:
                img_data = (img_data / np.max(img_data)) * 255.0
            img_uint8 = img_data.astype(np.uint8)
            
            # Apply CLAHE to enhance contrast (sonar images need this)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            img_enhanced = clahe.apply(img_uint8)
            
            out_path = os.path.join(output_dir, f"{base_name}_{side}.png")
            cv2.imwrite(out_path, img_enhanced)
            generated_images.append(out_path)
            
    return generated_images
