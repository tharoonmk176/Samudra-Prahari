import os
import glob
import cv2
import shutil

def add_subpipe(src_dir, dest_dir, class_id=2):
    img_dir = os.path.join(src_dir, "Image")
    txt_dir = os.path.join(src_dir, "YOLO_Annotation")
    
    txt_files = glob.glob(os.path.join(txt_dir, "*.txt"))
    print(f"Found {len(txt_files)} YOLO annotation files in SubPipe.")
    
    count = 0
    for txt_file in txt_files:
        # Check if text file actually has lines (i.e. recognizable pipes)
        with open(txt_file, "r") as f:
            lines = f.readlines()
            
        if not lines:
            continue # Skip empty background files
            
        # Format the lines to use our Class ID (2 for pipe)
        yolo_lines = []
        for line in lines:
            parts = line.strip().split()
            if len(parts) >= 5:
                yolo_lines.append(f"{class_id} " + " ".join(parts[1:]))
                
        if not yolo_lines:
            continue
            
        # Get matching image
        base_name = os.path.basename(txt_file).replace('.txt', '')
        img_path = os.path.join(img_dir, f"{base_name}.pbm")
        
        if not os.path.exists(img_path):
            continue
            
        # Read and convert PBM to JPG
        img = cv2.imread(img_path)
        if img is None:
            continue
            
        out_name = f"subpipe_{base_name}"
        
        # Save to Ultimate_Marine_Dataset
        cv2.imwrite(os.path.join(dest_dir, "images", "train", f"{out_name}.jpg"), img)
        with open(os.path.join(dest_dir, "labels", "train", f"{out_name}.txt"), "w") as f:
            f.write("\n".join(yolo_lines))
            
        count += 1
        # Stop at 300 to keep the dataset classes balanced
        if count >= 300:
            break
            
    print(f"Successfully ported {count} highly-recognizable SubPipe images to the Ultimate Dataset!")

if __name__ == "__main__":
    src = "dataset/Nexus/SubPipeMini/SubPipeMiniSSS/DATA/SSS_HF_images"
    dest = "Ultimate_Marine_Dataset"
    add_subpipe(src, dest, class_id=2)
