# 🌊 Samudra Prahari

**AI-Powered Automated Underwater Marine Debris & Anomaly Detection System**
*Ministry of Earth Sciences (MoES) | NIOT | Problem Statement ID: 26057*

An automated, edge-capable computer vision pipeline designed to ingest Side-Scan Sonar (SSS) imagery, stitch it into contiguous acoustic maps, identify man-made marine debris (such as Ghost Nets and Shipwrecks), and generate actionable geo-anchored intelligence reports for ocean cleanup operations.

---

## 🚀 Key Features

*   **Custom YOLOv8 Object Detection**
    *   Trained on a massively compiled dataset combining **SCTD** (Shipwrecks, Aircraft, Humans), **KLSG** (Seabed Objects), and purely synthetic physics-based generations.
    *   Optimized for deployment on marine edge devices (AUVs) to autonomously detect Shipwrecks, Aircraft, Pipes, Cylinders, and Entangled Ghost Nets.
*   **Acoustic Map Stitcher**
    *   Seamlessly stitches individual raw sonar swaths into one contiguous, massive waterfall map.
    *   Supports dynamic selection between Vertical (end-to-end) and Horizontal (side-by-side) map stitching based on survey lines.
*   **Sonar-Specific DSP Preprocessing Engine**
    *   **Speckle Denoising:** Gentle median filtering to suppress acoustic speckle noise without destroying vital geometric edges.
    *   **Nadir Masking:** Isolates and masks the central water-column blind zone to prevent false detections in the acoustic gap.
    *   **Slant-Range Correction:** Corrects geometric distortion based on towfish altitude.
*   **Intelligent Geo-Referencing**
    *   Dynamically maps physical Lat/Long coordinates to detected debris by mathematically tracking pixel offsets across the sonar mosaic based on user-provided towfish start coordinates and speed.
    *   Calculates the exact physical bounding dimensions (in meters) of every piece of debris.
*   **Streamlit Command Dashboard**
    *   A production-ready UI for marine technologists.
    *   Provides both a Master Acoustic Mosaic map and an Individual Strip Breakdown (with expanders for granular analysis).
    *   1-Click downloads for structured Intelligence Reports (`.CSV` and `.JSON`).
*   **Procedural Synthetic Generation**
    *   Because large datasets for Ghost Nets do not exist, we built a physics-based OpenCV engine that procedurally generates highly realistic, tangled ghost nets, casts accurate acoustic shadows, and blends them into raw sonar backgrounds.

---

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
# Alternatively: streamlit run app.py --server.fileWatcherType none
```

**3. Test the UI**
*   Upload sequence images from the `data/dummy_strips/` or `data/Ultimate_Marine_Dataset/` folders.
*   Configure DSP toggles and Geo-Anchoring coordinates in the sidebar.
*   Click **Generate Seamless Acoustic Map & Analyze**.

---

## 📁 Repository Structure

The codebase is highly modular, separating core engine components from raw data and training scripts.

*   `app.py`: The main Streamlit User Interface and orchestration pipeline.
*   `acoustic_map_pipeline.py`: Logic for continuous map stitching and bounding box aggregation.
*   `preprocess.py`: Digital Signal Processing (DSP) algorithms.
*   `shadow_filter.py`: Classical CV geometric shadow analysis.
*   `geo_report.py`: Lat/Long calculations and CSV/JSON report generation.
*   **`scripts/`**: Contains 19+ utility scripts (dataset compilation, ONNX exporting, synthetic generation, and testing).
*   **`notebooks/`**: Jupyter/Colab notebooks for YOLOv8 model training.
*   **`data/`**: Consolidated datasets (SCTD, synthetic nets, dummy strips).
*   **`models/`**: Stores the compiled `best.pt` and `best.onnx` YOLO weights.
*   **`outputs/`**: The designated output directory for all exported reports and annotated map images.
*   **`archives/`**: Storage for massive ZIP files and dataset backups.
