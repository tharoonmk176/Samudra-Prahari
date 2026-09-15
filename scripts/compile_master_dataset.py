import os
import shutil
import glob
import cv2
import numpy as np
import xml.etree.ElementTree as ET

# Master classes: ['shipwreck', 'aircraft', 'pipe', 'cylinder', 'ghost_net']
# IDs:                 0            1          2         3           4

def setup_dirs(base_dir):
    if os.path.exists(base_dir):
        shutil.rmtree(base_dir)
    os.makedirs(f"{base_dir}/images/train", exist_ok=True)
    os.makedirs(f"{base_dir}/labels/train", exist_ok=True)
    return base_dir

def process_ai4(dest):
    print("Processing AI4Shipwrecks (Masks -> YOLO boxes for Class 0)...")
    masks = glob.glob("dataset/AI4Shipwrecks/train/labels/*.png")
    count = 0
    for mask_path in masks:
        mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
        if mask is None or np.max(mask) == 0:
            continue
        
        # Find contours of the shipwreck mask
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        H, W = mask.shape
        yolo_lines = []
        for cnt in contours:
            if cv2.contourArea(cnt) < 50: continue
            x, y, w, h = cv2.boundingRect(cnt)
            cx = (x + w/2) / W
            cy = (y + h/2) / H
            bw = w / W
            bh = h / H
            yolo_lines.append(f"0 {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}")
            
        if yolo_lines:
            img_path = mask_path.replace("labels", "images")
            if os.path.exists(img_path):
                img_name = f"ai4_{os.path.basename(img_path)}"
                # Convert PNG to JPG to save space/standardize
                img = cv2.imread(img_path)
                if img is not None:
                    cv2.imwrite(f"{dest}/images/train/{img_name.replace('.png', '.jpg')}", img)
                    with open(f"{dest}/labels/train/{img_name.replace('.png', '.txt')}", "w") as f:
                        f.write("\n".join(yolo_lines))
                    count += 1
                    if count >= 300: break # Keep dataset balanced
    print(f"-> Added {count} AI4Shipwrecks")

def process_sctd(dest):
    print("Processing SCTD (XMLs -> YOLO for Classes 0, 1)...")
    xmls = glob.glob("SCTD/SCTD/Annotations/*.xml")
    count_s = 0; count_a = 0
    for xml_file in xmls:
        root = ET.parse(xml_file).getroot()
        size = root.find('size')
        if size is None: continue
        W = int(size.find('width').text)
        H = int(size.find('height').text)
        
        yolo_lines = []
        for obj in root.findall('object'):
            name = obj.find('name').text
            if name == 'ship': cls_id = 0; count_s+=1
            elif name == 'aircraft': cls_id = 1; count_a+=1
            else: continue
            
            box = obj.find('bndbox')
            xmin = float(box.find('xmin').text); xmax = float(box.find('xmax').text)
            ymin = float(box.find('ymin').text); ymax = float(box.find('ymax').text)
            cx = ((xmin+xmax)/2)/W; cy = ((ymin+ymax)/2)/H
            bw = (xmax-xmin)/W; bh = (ymax-ymin)/H
            yolo_lines.append(f"{cls_id} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}")
            
        if yolo_lines:
            img_name = root.find('filename').text
            img_path = os.path.join("SCTD/SCTD/JPEGImages", img_name)
            if os.path.exists(img_path):
                out_name = f"sctd_{img_name}"
                shutil.copy(img_path, f"{dest}/images/train/{out_name}")
                with open(f"{dest}/labels/train/{out_name.replace('.jpg', '.txt')}", "w") as f:
                    f.write("\n".join(yolo_lines))
    print(f"-> Added {count_s} ships and {count_a} aircraft")

def process_uatd(dest):
    print("Processing UATD (XMLs -> YOLO for Class 3 [cylinder])...")
    xmls = glob.glob("pipe/UATD/UATD_Training/annotations/*.xml")
    if not xmls:
        print("-> UATD XMLs not found. Skipping.")
        return
        
    count = 0
    for xml_file in xmls:
        root = ET.parse(xml_file).getroot()
        size = root.find('size')
        if size is None: continue
        W = int(size.find('width').text)
        H = int(size.find('height').text)
        
        yolo_lines = []
        for obj in root.findall('object'):
            if obj.find('name').text == 'cylinder':
                box = obj.find('bndbox')
                xmin = float(box.find('xmin').text); xmax = float(box.find('xmax').text)
                ymin = float(box.find('ymin').text); ymax = float(box.find('ymax').text)
                cx = ((xmin+xmax)/2)/W; cy = ((ymin+ymax)/2)/H
                bw = (xmax-xmin)/W; bh = (ymax-ymin)/H
                yolo_lines.append(f"3 {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}")
                
        if yolo_lines:
            filename_node = root.find('filename')
            if filename_node is not None and filename_node.text:
                img_name = filename_node.text
            else:
                img_name = os.path.basename(xml_file).replace('.xml', '.bmp')
                
            img_path = os.path.join("pipe/UATD/UATD_Training/images", img_name)
            if os.path.exists(img_path):
                # Convert BMP to JPG
                img = cv2.imread(img_path)
                out_name = f"uatd_{img_name.replace('.bmp', '.jpg')}"
                cv2.imwrite(f"{dest}/images/train/{out_name}", img)
                with open(f"{dest}/labels/train/{out_name.replace('.jpg', '.txt')}", "w") as f:
                    f.write("\n".join(yolo_lines))
                count += 1
                if count >= 300: break # Keep balanced
    print(f"-> Added {count} cylinders")

def process_20xx_pipes(dest):
    print("Processing 20xx for Pipes (Class 2)...")
    txts = glob.glob("dataset/Nexus/2010/**/*.txt", recursive=True)
    count = 0
    for txt in txts:
        if "classes" in txt: continue
        with open(txt, "r") as f: lines = f.readlines()
        yolo_lines = []
        for l in lines:
            parts = l.strip().split()
            if not parts: continue
            # Class 0 in 20xx was pipes. Class 1 was cylinders (which we replaced with UATD)
            if parts[0] == '0':
                yolo_lines.append(f"2 " + " ".join(parts[1:]))
        
        if yolo_lines:
            img_path = txt.replace('.txt', '.jpg')
            if os.path.exists(img_path):
                out_name = f"pipe20xx_{os.path.basename(img_path)}"
                shutil.copy(img_path, f"{dest}/images/train/{out_name}")
                with open(f"{dest}/labels/train/{out_name.replace('.jpg', '.txt')}", "w") as f:
                    f.write("\n".join(yolo_lines))
                count += 1
                if count >= 300: break
    print(f"-> Added {count} pipes")

def process_ghost_nets(dest):
    print("Processing Synthetic Ghost Nets (Class 4)...")
    imgs = glob.glob("synthetic_nets/images/*.jpg")
    for img in imgs[:300]:
        txt = img.replace("images", "labels").replace(".jpg", ".txt")
        if not os.path.exists(txt): continue
        
        with open(txt, "r") as f: lines = f.readlines()
        yolo_lines = []
        for l in lines:
            parts = l.strip().split()
            if parts: yolo_lines.append(f"4 " + " ".join(parts[1:]))
            
        out_name = f"synth_{os.path.basename(img)}"
        shutil.copy(img, f"{dest}/images/train/{out_name}")
        with open(f"{dest}/labels/train/{out_name.replace('.jpg', '.txt')}", "w") as f:
            f.write("\n".join(yolo_lines))
    print(f"-> Added {len(imgs[:300])} ghost nets")

def write_yaml(dest):
    content = "train: images/train\nval: images/train\nnc: 5\nnames: ['shipwreck', 'aircraft', 'pipe', 'cylinder', 'ghost_net']"
    with open(f"{dest}/data.yaml", "w") as f: f.write(content)

if __name__ == "__main__":
    dest = setup_dirs("Ultimate_Marine_Dataset")
    process_ai4(dest)
    process_sctd(dest)
    process_uatd(dest)
    process_20xx_pipes(dest)
    process_ghost_nets(dest)
    write_yaml(dest)
    print("\nDataset successfully compiled to Ultimate_Marine_Dataset!")
