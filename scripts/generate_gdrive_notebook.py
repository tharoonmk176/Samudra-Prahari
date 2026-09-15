import json

notebook = {
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# Phase 1: YOLOv8 Marine Debris Training (Google Drive Workflow)\n",
    "This notebook trains the YOLOv8n model on the pre-compiled `Final_Training_Dataset` containing:\n",
    "1. **Shipwrecks & Aircraft**\n",
    "2. **Pipes & Cylinders**\n",
    "3. **Ghost Nets**\n",
    "\n",
    "**Instructions:**\n",
    "1. Upload `Final_Training_Dataset.zip` to the root of your Google Drive.\n",
    "2. Run the cells below. The notebook will extract the data to the fast local Colab disk, train, and save the final model back to your Drive."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "from google.colab import drive\n",
    "drive.mount('/content/drive')"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "!pip install ultralytics\n",
    "import os\n",
    "import shutil\n",
    "\n",
    "# Unzip from Drive to LOCAL Colab disk (crucial for GPU read speeds)\n",
    "print(\"Extracting dataset to local disk...\")\n",
    "!unzip -q /content/drive/MyDrive/Final_Training_Dataset.zip -d /content/\n",
    "print(\"Dataset extracted successfully!\")"
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
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Copy the trained weights back to Google Drive to persist them\n",
    "import shutil\n",
    "\n",
    "trained_pt = \"/content/runs/detect/train/weights/best.pt\"\n",
    "trained_onnx = \"/content/runs/detect/train/weights/best.onnx\"\n",
    "\n",
    "if os.path.exists(trained_pt):\n",
    "    shutil.copy(trained_pt, \"/content/drive/MyDrive/marine_debris_best.pt\")\n",
    "    print(\"Saved best.pt to Google Drive!\")\n",
    "\n",
    "if os.path.exists(trained_onnx):\n",
    "    shutil.copy(trained_onnx, \"/content/drive/MyDrive/marine_debris_best.onnx\")\n",
    "    print(\"Saved best.onnx to Google Drive!\")\n"
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
