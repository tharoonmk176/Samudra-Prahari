import os
import shutil
import glob
import xml.etree.ElementTree as ET

def process_sctd(dest_dir):
    print("Processing SCTD Dataset (Shipwrecks & Aircraft)...")
    xml_files = glob.glob('SCTD/SCTD/Annotations/*.xml')
    if not xml_files:
        print("SCTD XMLs not found! Make sure 'SCTD/SCTD/Annotations' exists.")
        return
        
    count_ship = 0
    count_aircraft = 0
    
    for xml_file in xml_files:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        img_name = root.find('filename').text
        
        size = root.find('size')
        if size is None: continue
        W = int(size.find('width').text)
        H = int(size.find('height').text)
        
        yolo_lines = []
        for obj in root.findall('object'):
            name = obj.find('name').text
            if name == 'ship': 
                cls_id = 0
                count_ship += 1
            elif name == 'aircraft': 
                cls_id = 1
                count_aircraft += 1
            else: 
                continue # Ignore human and ChaojieZhu
            
            bndbox = obj.find('bndbox')
            xmin = float(bndbox.find('xmin').text)
            xmax = float(bndbox.find('xmax').text)
            ymin = float(bndbox.find('ymin').text)
            ymax = float(bndbox.find('ymax').text)
            
            cx = ((xmin + xmax) / 2) / W
            cy = ((ymin + ymax) / 2) / H
            w = (xmax - xmin) / W
            h = (ymax - ymin) / H
            
            yolo_lines.append(f"{cls_id} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")
            
        if yolo_lines:
            img_src = os.path.join('SCTD/SCTD/JPEGImages', img_name)
            if os.path.exists(img_src):
                out_name = f"sctd_{img_name}"
                shutil.copy(img_src, os.path.join(dest_dir, "images", "train", out_name))
                with open(os.path.join(dest_dir, "labels", "train", out_name.replace('.jpg', '.txt')), 'w') as f:
                    f.write("\n".join(yolo_lines))
                    
    print(f"Added {count_ship} shipwrecks and {count_aircraft} aircraft to the dataset.")

if __name__ == "__main__":
    dest = "Final_Training_Dataset"
    process_sctd(dest)
