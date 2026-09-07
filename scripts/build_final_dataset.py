import os
import shutil
import glob
import random
import xml.etree.ElementTree as ET

def setup_directories(base_dir):
    if os.path.exists(base_dir):
        shutil.rmtree(base_dir)
    os.makedirs(os.path.join(base_dir, "images", "train"), exist_ok=True)
    os.makedirs(os.path.join(base_dir, "labels", "train"), exist_ok=True)
    return base_dir

def copy_20xx_data(dest_dir):
    print("Processing 20xx Datasets (Pipes/Cylinders)...")
    years = ["2010", "2015", "2017", "2018", "2021"]
    
    count = 0
    for year in years:
        search_path = os.path.join("dataset/Nexus", year, "**", "*.txt")
        txt_files = glob.glob(search_path, recursive=True)
        
        for txt_file in txt_files:
            if "classes" in txt_file or not txt_file.endswith('.txt'):
                continue
            
            img_file = txt_file.replace('.txt', '.jpg')
            if not os.path.exists(img_file):
                continue
                
            # Read and map labels: 20xx has classes 0 and 1. 
            # We map 0 -> 2 (pipe), 1 -> 3 (cylinder)
            with open(txt_file, 'r') as f:
                lines = f.readlines()
                
            new_lines = []
            for line in lines:
                parts = line.strip().split()
                if not parts: continue
                
                cls_id = int(parts[0])
                if cls_id == 0:
                    new_cls = 2
                elif cls_id == 1:
                    new_cls = 3
                else:
                    continue # Skip unknowns
                    
                new_lines.append(f"{new_cls} " + " ".join(parts[1:]))
                
            if not new_lines:
                continue
                
            out_name = f"20xx_{year}_{os.path.basename(img_file)}"
            
            shutil.copy(img_file, os.path.join(dest_dir, "images", "train", out_name))
            with open(os.path.join(dest_dir, "labels", "train", out_name.replace('.jpg', '.txt')), 'w') as f:
                f.write("\n".join(new_lines))
                
            count += 1
            if count >= 300: # Limit to 300 to keep it balanced
                return

def copy_synthetic_nets(dest_dir):
    print("Processing Synthetic Ghost Nets...")
    img_files = glob.glob("synthetic_nets/images/*.jpg")
    
    for img_file in img_files[:200]: # Sample 200
        txt_file = img_file.replace('images', 'labels').replace('.jpg', '.txt')
        if not os.path.exists(txt_file):
            continue
            
        out_name = f"synth_{os.path.basename(img_file)}"
        shutil.copy(img_file, os.path.join(dest_dir, "images", "train", out_name))
        
        # Synthetic is already labeled as class 3, but in our new scheme it should be 4
        with open(txt_file, 'r') as f:
            lines = f.readlines()
            
        new_lines = []
        for line in lines:
            parts = line.strip().split()
            if parts:
                new_lines.append(f"4 " + " ".join(parts[1:]))
                
        with open(os.path.join(dest_dir, "labels", "train", out_name.replace('.jpg', '.txt')), 'w') as f:
            f.write("\n".join(new_lines))

def write_yaml(dest_dir):
    yaml_content = f"""train: images/train
val: images/train

nc: 5
names: ['shipwreck', 'aircraft', 'pipe', 'cylinder', 'ghost_net']
"""
    with open(os.path.join(dest_dir, "data.yaml"), 'w') as f:
        f.write(yaml_content)

if __name__ == "__main__":
    dest = setup_directories("Final_Training_Dataset")
    
    # We will let Colab handle SCTD downloading and processing, 
    # but here we bundle the local 20xx and Synthetic datasets!
    copy_20xx_data(dest)
    copy_synthetic_nets(dest)
    write_yaml(dest)
    
    print("Done! Dataset compiled at:", dest)
