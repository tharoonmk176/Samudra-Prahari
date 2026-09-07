import json

notebook = {
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# Phase 1: YOLOv8 Marine Debris Training\n",
    "This notebook trains the YOLOv8n model on the pre-compiled `Final_Training_Dataset` containing:\n",
    "1. **Shipwrecks & Aircraft**\n",
    "2. **Pipes & Cylinders**\n",
    "3. **Ghost Nets**\n",
    "\n",
    "Please upload `Final_Training_Dataset.zip` to your Colab workspace before running."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "!pip install ultralytics\n",
    "\n",
    "# Unzip the uploaded dataset\n",
    "!unzip -q Final_Training_Dataset.zip -d /content/\n",
    "print(\"Dataset unzipped successfully!\")"
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
