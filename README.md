# Samudra Prahari — AI-Powered Marine Debris Detection

**Ministry of Earth Sciences (MoES) | NIOT | Problem Statement ID: 26057**

An advanced, full-stack, edge-capable computer vision pipeline that ingests Side-Scan Sonar (SSS) imagery, stitches it into contiguous acoustic maps, identifies man-made marine debris using a Multi-Stage AI Pipeline, and generates actionable geo-anchored intelligence reports.

## Getting Started

### Prerequisites
- Node.js (v18+)
- Python 3.10+
- Docker and Docker Compose

### Option 1: Run via Docker Compose (Recommended)
You can launch the entire stack (Frontend + Backend) with a single command:
```bash
docker-compose up --build
```
- Frontend will be available at: `http://localhost:3000`
- Backend API will be available at: `http://localhost:8000`

### Option 2: Run Locally (Development Mode)

**1. Start the FastAPI Backend**
```bash
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
pip install -r backend/requirements.txt
cd backend
uvicorn api:app --host 0.0.0.0 --port 8000
```

**2. Start the Next.js Frontend**
Open a new terminal window:
```bash
cd frontend
npm install
npm run dev
```
Navigate to `http://localhost:3000` to view the dashboard.

---

## AI Model Training Details & Dataset Sources

The three core AI models in the Samudra Prahari V3 pipeline were trained using a master compiled dataset fused from multiple public and custom synthetic sources. In total, the main training volume consisted of **3,069 high-resolution side-scan sonar images** (2,730 for training, 339 for validation).

Here is the exact breakdown of the image counts, target classes, and data sources used to train the three core models:

| Model | Role | Total Images | Target Classes | Data Sources Fused |
| :--- | :--- | :--- | :--- | :--- |
| **Anomaly Autoencoder**<br>`stage_a_ae.onnx` | Learns the normal seabed background to flag statistical anomalies. | **641**<br>*(Train: 641)* | None (Clean Seabed / Background Only) | • [**SCTD**](https://github.com/MingqiangNing/SCTD) (Filtered subset of empty, featureless sand/rock patches) |
| **YOLO11n Classifier**<br>`yolo11n.onnx` | Draws bounding boxes and strictly classifies rigid structures and debris. | **3,069**<br>*(Train: 2,730)*<br>*(Val: 339)* | Shipwreck, Aircraft, Cylinder, Pipe, Ghost Net | • [**AI4Shipwrecks**](https://github.com/dzt-1122/AI4Shipwrecks)<br>• [**SCTD**](https://github.com/MingqiangNing/SCTD) (Seabed Contraband)<br>• [**UATD**](https://figshare.com/articles/dataset/UATD_Dataset/21331143) (Acoustic Targets)<br>• [**SubPipe**](https://github.com/remaro-network/SubPipe-dataset) (Pipes)<br>• **Custom Synthetic Engine** (Ghost Nets) |
| **U-Net Segmentation**<br>`stage_b_unet.onnx` | Predicts pixel-perfect physical boundaries (Binary Foreground vs Background). | **~3,000**<br>*(Train: 2,730)*<br>*(Val: 339)* | Shipwreck, Aircraft, Cylinder, Pipe, Ghost Net | • Exact same sources as YOLO, but trained using **binary pixel masks** instead of bounding box coordinates. |
