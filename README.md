# Samudra Prahari — AI-Powered Marine Debris Detection

**Ministry of Earth Sciences (MoES) | NIOT | Problem Statement ID: 26057**

An automated, edge-capable computer vision pipeline that ingests Side-Scan Sonar (SSS) imagery, stitches it into contiguous acoustic maps, identifies man-made marine debris (Ghost Nets, Shipwrecks, Aircraft, Pipes, Cylinders), and generates actionable geo-anchored intelligence reports.

---

## Key Features

### Custom YOLOv8 Object Detection
- Trained on compiled SCTD and KLSG datasets
- Optimized for edge deployment on marine AUVs (ONNX export)

### Adaptive Lee Speckle Filter *(Upgraded)*
- **Lee filter** instead of median blur — preserves thin ghost-net structures and 1px filaments that median filtering would destroy
- Smooths flat speckle noise while keeping high-variance edges intact

### Behind-Box Acoustic Shadow Analysis *(Upgraded)*
- Reads the acoustic shadow **behind** each detection (far-from-nadir side)
- Scores three cues: **solidity** (convexity), **regularity** (constant width), **contrast** (darkness vs seabed)
- Class-aware: ghost nets get inverted scoring (chaotic shadow = positive signal)
- Recalibrates YOLO confidence, rejecting rock/shadow false positives

### Geodesic Geo-Referencing *(Upgraded)*
- **pyproj WGS84** ellipsoidal geodesic math instead of crude pixel-based approximation
- Proper forward-solve for across-track and along-track offset → lat/lon

### Physical Dimension Calculation *(Upgraded)*
- Computes **width_m × height_m** from sonar resolution (m/px)
- Reports full provenance: `yolo_conf`, `shadow_score`, `calibrated_conf`

### Acoustic Map Stitcher
- Stitches individual strips into contiguous waterfall maps
- Supports Vertical (end-to-end) and Horizontal (side-by-side) stitching

### Streamlit Command Dashboard
- Premium UI with interactive Folium geo-maps
- Per-strip expander breakdown with shadow score details
- 1-click CSV/JSON intelligence report downloads

---

## How to Run

### 1. Install Dependencies

```bash
python -m venv venv
source venv/bin/activate
pip install streamlit pandas folium streamlit-folium opencv-python numpy ultralytics pyproj
```

### 2. Launch the Dashboard

```bash
streamlit run app.py --server.fileWatcherType none
# or
./run_dashboard.sh
```

### 3. Use the Dashboard
1. Upload sonar strip images (.jpg/.png)
2. Toggle DSP preprocessing in the sidebar (Lee filter, nadir masking, slant-range correction)
3. Set nadir side for shadow analysis
4. Optionally enable geo-anchoring with start coordinates
5. Click **Generate Seamless Acoustic Map & Analyze**

---

## Repository Structure

```
├── app.py                    # Streamlit dashboard (orchestration)
├── preprocess.py             # DSP: Lee filter, slant-range, nadir, normalize
├── shadow_filter.py          # Behind-box shadow scoring + YOLO recalibration
├── geo_report.py             # pyproj geodesic geo-referencing + report gen
├── acoustic_map_pipeline.py  # Strip stitching + mosaic detection
├── scripts/                  # 19+ utility scripts
│   ├── synth_net.py          # Ghost-net data generation utility
│   ├── voc2yolo.py           # SCTD VOC→YOLO converter
│   ├── train_yolo.py         # YOLOv8 training
│   └── ...
├── notebooks/                # Colab training notebooks
├── models/GhostNetSonar/     # Trained weights (best.pt, best.onnx)
└── outputs/                  # Generated reports and annotated maps
```

---

## Pipeline Architecture

```
Raw Sonar Strips
      │
      ▼
┌─────────────────────────────────┐
│  DSP Preprocessing              │
│  • Lee speckle filter           │
│  • Slant-range correction       │
│  • Nadir masking                │
│  • Percentile normalization     │
└─────────────┬───────────────────┘
              │
              ▼
┌─────────────────────────────────┐
│  Acoustic Map Stitcher          │
│  • Vertical / Horizontal concat │
│  • Coordinate offset tracking   │
└─────────────┬───────────────────┘
              │
              ▼
┌─────────────────────────────────┐
│  YOLOv8n Detection              │
│  • 5 classes: Ship, Aircraft,   │
│    Pipe, Cylinder, Ghost Net    │
└─────────────┬───────────────────┘
              │
              ▼
┌─────────────────────────────────┐
│  Shadow Verification Filter     │
│  • Read shadow BEHIND the box   │
│  • Score: solidity + regularity │
│    + contrast                   │
│  • Recalibrate confidence       │
│  • Reject false positives       │
└─────────────┬───────────────────┘
              │
              ▼
┌─────────────────────────────────┐
│  Geo-Referencing (pyproj)       │
│  • Pixel → slant → ground range │
│  • Geodesic forward solve       │
│  • Physical dimensions (m)      │
└─────────────┬───────────────────┘
              │
              ▼
┌─────────────────────────────────┐
│  Intelligence Reports           │
│  • JSON (with CRS: EPSG:4326)  │
│  • CSV with full provenance     │
│  • Interactive Folium map       │
└─────────────────────────────────┘
```

---

## Honest Caveats

- **Geo-coordinates require real nav metadata.** Without GPS/XTF, coordinates are null (never fabricated).
- The shadow filter is classical CV. Calibrate the weights on your operational data.
