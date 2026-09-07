# 🌊 Ghost-Net Sonar Analytics Engine

An automated edge-computing pipeline for detecting man-made marine debris and ghost nets in Side-Scan Sonar (SSS) imagery. Built as a comprehensive solution spanning deep learning, classical computer vision, and geographic mapping.

## 🚀 Features (The 6-Phase Architecture)

*   **Phase 1: Deep Learning (YOLOv8 Edge)**
    *   Trained on a merged heavy dataset combining the **SCTD** (ships, aircraft, humans) and **KLSG** (seabed objects) open datasets.
    *   Exported to ONNX format for rapid, CPU-friendly inference on edge devices (like marine AUVs).
*   **Phase 2: Sonar-Specific DSP Preprocessing**
    *   **Gentle Median Filtering** removes acoustic speckle noise without destroying vital geometric edges.
    *   **Dynamic Nadir Masking** isolates and inpaints the central water column blind zone to prevent false detections in the acoustic gap.
    *   **Percentile-Based Contrast Normalization** balances the intense brightness of acoustic highlights against the dark seafloor.
*   **Phase 3: Geometric Shadow Filtering (Classical CV)**
    *   *The Problem:* YOLO models frequently mistake jagged rocks for man-made debris because they look similar in side-scan sonar.
    *   *The Solution:* We extract the bounding box of every YOLO detection and apply Otsu's thresholding to isolate the acoustic shadow. We then mathematically calculate the shadow's **Solidity** (Contour Area / Convex Hull Area) and **Complexity** (Perimeter-to-Area ratio).
    *   If the shadow is highly jagged (rock), confidence is slashed. If it is highly geometric (man-made), confidence is maintained.
*   **Phases 4 & 5: Geo-Referencing & Reporting**
    *   Automatically calculates the physical meter offset of anomalies from the sonar towfish path (Across-track and Along-track distances).
    *   Generates flattened, structured JSON and CSV reports detailing `lat`, `long`, `bounding_dimensions_m`, `class`, and `confidence`.
*   **Phase 6: Interactive Dashboard**
    *   A premium, dark-mode Streamlit UI.
    *   Supports batch uploading of sonar waterfall imagery.
    *   Simulates a live **Folium Acoustic Map**, mapping detections directly onto geographic coordinates.
*   **Phase X: Synthetic Ghost Net Generator**
    *   Because public bounding-box datasets for ghost nets do not exist, we built a procedural OpenCV generator.
    *   It creates tangled mesh grids using elastic sinusoidal warping (`cv2.remap`), casts realistic acoustic shadows, blends them into sonar background noise, and automatically outputs perfect YOLO bounding box `.txt` labels.

## 🛠️ How to Run

**1. Install Dependencies**
```bash
python -m venv venv
source venv/bin/activate
pip install streamlit pandas folium streamlit-folium opencv-python numpy ultralytics
```

**2. Launch the Analytics Dashboard**
```bash
./run_dashboard.sh
```
*(Note: The Streamlit file-watcher is intentionally disabled in the launch script to prevent the UI from auto-refreshing during batch image saving).*

**3. Generate Synthetic Ghost Nets**
```bash
python synth_net.py
```
*(This will generate synthetic nets and labels in the `synthetic_nets/` folder).*

**4. Retrain the YOLO Model**
Upload `Phase1_Train.ipynb` to Google Colab. The notebook will automatically download the SCTD and KLSG datasets, generate 500 synthetic nets, merge the data formats, and train a new `yolov8n.pt` model on a T4 GPU.

## 📁 Repository Structure
*   `app.py`: Main Streamlit UI and pipeline orchestration.
*   `preprocess.py`: DSP algorithms (Denoising, Nadir masking).
*   `shadow_filter.py`: Classical CV geometry logic and YOLO inference.
*   `geo_report.py`: JSON/CSV generation and pixel-to-meter translation.
*   `synth_net.py`: Procedural ghost-net data generator.
*   `outputs/`: Stores all generated CSVs, JSONs, and annotated images.
