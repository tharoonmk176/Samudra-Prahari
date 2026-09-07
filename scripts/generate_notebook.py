import json

notebook = {
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# Phase 1: Heavy Dataset Merger & YOLOv8 Retraining\n",
    "This notebook compiles the final dataset matching the MoES Problem Statement requirements:\n",
    "1. **Shipwrecks & Aircraft** (Sourced from SCTD)\n",
    "2. **Pipes & Cylinders** (Sourced from Nexus 20xx Datasets)\n",
    "3. **Ghost Nets** (Sourced from our Procedural Synthetic Generator)\n",
    "\n",
    "Upload your `Final_Training_Dataset.zip` to Colab before running."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "!pip install ultralytics opencv-python\n",
    "import os\n",
    "import shutil\n",
    "import xml.etree.ElementTree as ET\n",
    "import glob\n",
    "\n",
    "# 1. Unzip the local dataset we uploaded (Pipes, Cylinders, Ghost Nets)\n",
    "!unzip -q Final_Training_Dataset.zip -d /content/\n"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "# 2. Download and Process SCTD (Shipwrecks & Aircraft)\n",
    "!git clone https://github.com/freepoet/SCTD.git\n",
    "!unzip -q SCTD/SCTD.zip -d /content/SCTD_extracted/\n",
    "\n",
    "xml_files = glob.glob('/content/SCTD_extracted/SCTD/Annotations/*.xml')\n",
    "for xml_file in xml_files:\n",
    "    tree = ET.parse(xml_file)\n",
    "    root = tree.getroot()\n",
    "    img_name = root.find('filename').text\n",
    "    \n",
    "    # Get dimensions\n",
    "    size = root.find('size')\n",
    "    W = int(size.find('width').text)\n",
    "    H = int(size.find('height').text)\n",
    "    \n",
    "    yolo_lines = []\n",
    "    for obj in root.findall('object'):\n",
    "        name = obj.find('name').text\n",
    "        if name == 'ChaojieZhu' or name == 'human': \n",
    "            continue # Drop junk and out-of-scope classes\n",
    "            \n",
    "        if name == 'ship': cls_id = 0\n",
    "        elif name == 'aircraft': cls_id = 1\n",
    "        else: continue\n",
    "        \n",
    "        bndbox = obj.find('bndbox')\n",
    "        xmin = float(bndbox.find('xmin').text)\n",
    "        xmax = float(bndbox.find('xmax').text)\n",
    "        ymin = float(bndbox.find('ymin').text)\n",
    "        ymax = float(bndbox.find('ymax').text)\n",
    "        \n",
    "        cx = ((xmin + xmax) / 2) / W\n",
    "        cy = ((ymin + ymax) / 2) / H\n",
    "        w = (xmax - xmin) / W\n",
    "        h = (ymax - ymin) / H\n",
    "        yolo_lines.append(f\"{cls_id} {cx} {cy} {w} {h}\")\n",
    "        \n",
    "    if yolo_lines:\n",
    "        img_src = os.path.join('/content/SCTD_extracted/SCTD/JPEGImages', img_name)\n",
    "        if os.path.exists(img_src):\n",
    "            # Copy to our final dataset\n",
    "            shutil.copy(img_src, os.path.join('/content/Final_Training_Dataset/images/train', img_name))\n",
    "            with open(os.path.join('/content/Final_Training_Dataset/labels/train', img_name.replace('.jpg', '.txt')), 'w') as f:\n",
    "                f.write(\"\\n\".join(yolo_lines))\n",
    "\n",
    "print(\"SCTD Successfully Merged into Final_Training_Dataset!\")\n"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "from ultralytics import YOLO\n",
    "\n",
    "# Retrain YOLO on the fully merged dataset (5 Classes)\n",
    "model = YOLO(\"yolov8n.pt\")\n",
    "results = model.train(\n",
    "    data=\"/content/Final_Training_Dataset/data.yaml\",\n",
    "    epochs=100,\n",
    "    imgsz=640,\n",
    "    batch=16,\n",
    "    device=\"0\"  # Run on GPU\n",
    ")\n",
    "\n",
    "# Export to ONNX for edge deployment\n",
    "model.export(format=\"onnx\")"
   ]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 4
}

with open('Phase1_Train.ipynb', 'w') as f:
    json.dump(notebook, f, indent=1)
