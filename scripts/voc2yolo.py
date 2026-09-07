import os
import glob
import xml.etree.ElementTree as ET
import random
import shutil
import yaml

def convert_voc_to_yolo():
    # Classes to keep, ChaojieZhu will be dropped
    classes = ['ship', 'aircraft', 'human']
    
    # Paths
    # Assuming SCTD dataset is unzipped in the current directory
    dataset_dir = 'SCTD'
    images_dir = os.path.join(dataset_dir, 'JPEGImages')
    annotations_dir = os.path.join(dataset_dir, 'Annotations')
    
    if not os.path.exists(dataset_dir):
        print(f"Error: Dataset directory '{dataset_dir}' not found. Please make sure to download and unzip SCTD first.")
        return
        
    output_dir = 'SCTD_YOLO'
    os.makedirs(output_dir, exist_ok=True)
    
    for split in ['train', 'val']:
        os.makedirs(os.path.join(output_dir, 'images', split), exist_ok=True)
        os.makedirs(os.path.join(output_dir, 'labels', split), exist_ok=True)
        
    # Get all XML files
    xml_files = glob.glob(os.path.join(annotations_dir, '*.xml'))
    random.seed(42) # For reproducibility
    random.shuffle(xml_files)
    
    # 80/20 split
    split_idx = int(0.8 * len(xml_files))
    train_files = xml_files[:split_idx]
    val_files = xml_files[split_idx:]
    
    def process_files(files, split):
        valid_files_count = 0
        for xml_file in files:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            # Image size
            size = root.find('size')
            w = int(size.find('width').text)
            h = int(size.find('height').text)
            
            filename = root.find('filename').text
            img_path = os.path.join(images_dir, filename)
            
            if not os.path.exists(img_path):
                print(f"Warning: Image {img_path} not found.")
                continue
                
            yolo_labels = []
            has_valid_objects = False
            
            for obj in root.iter('object'):
                cls_name = obj.find('name').text
                
                # Drop junk class
                if cls_name == 'ChaojieZhu' or cls_name not in classes:
                    continue
                    
                cls_id = classes.index(cls_name)
                xmlbox = obj.find('bndbox')
                
                # Bounding box coordinates
                xmin = float(xmlbox.find('xmin').text)
                xmax = float(xmlbox.find('xmax').text)
                ymin = float(xmlbox.find('ymin').text)
                ymax = float(xmlbox.find('ymax').text)
                
                # YOLO format: x_center, y_center, width, height (normalized 0-1)
                x_center = ((xmin + xmax) / 2) / w
                y_center = ((ymin + ymax) / 2) / h
                width = (xmax - xmin) / w
                height = (ymax - ymin) / h
                
                yolo_labels.append(f"{cls_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}")
                has_valid_objects = True
                
            if has_valid_objects:
                # Copy image to new split directory
                shutil.copy(img_path, os.path.join(output_dir, 'images', split, filename))
                
                # Write label to new split directory
                label_filename = os.path.splitext(filename)[0] + '.txt'
                with open(os.path.join(output_dir, 'labels', split, label_filename), 'w') as f:
                    f.write('\n'.join(yolo_labels))
                
                valid_files_count += 1
                
        return valid_files_count

    print(f"Processing training files...")
    train_count = process_files(train_files, 'train')
    print(f"Processing validation files...")
    val_count = process_files(val_files, 'val')
    
    print(f"Dataset conversion complete. Train images: {train_count}, Val images: {val_count}")
    
    # Create data.yaml
    data_yaml = {
        'path': os.path.abspath(output_dir),
        'train': 'images/train',
        'val': 'images/val',
        'names': {i: name for i, name in enumerate(classes)}
    }
    
    with open(os.path.join(output_dir, 'data.yaml'), 'w') as f:
        yaml.dump(data_yaml, f, sort_keys=False)
        
    print(f"Created data.yaml at {os.path.join(output_dir, 'data.yaml')}")
    print("Classes mapped as:")
    for i, name in enumerate(classes):
        print(f"  {i}: {name}")

if __name__ == '__main__':
    convert_voc_to_yolo()
