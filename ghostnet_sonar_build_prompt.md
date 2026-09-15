# Master Build Prompt — Ghost-Net / Marine Debris Detection in Side-Scan Sonar

*How to use this file: paste Sections 1–9 into your AI coding assistant (Colab AI / Cursor / Claude) as a single prompt. It defines the problem, the honest constraints, the architecture, the exact tools with links, and a phase-by-phase build order. It instructs the assistant to build one phase at a time and stop for your verification — do not let it dump everything at once.*

---

## 0. How the assistant must behave (read first)

```
You are helping me build an end-to-end computer-vision system for a hackathon. Build it
PHASE BY PHASE. After each phase: give runnable code, then STOP and tell me exactly how to
verify it works before continuing. Do not dump all phases at once. Flag every assumption you
make. Never claim data or accuracy that does not exist. Keep code modular (one clean function
or file per pipeline block) but in ONE repo/notebook — no microservices.
```

---

## 1. Problem Definition

Build an **end-to-end computer-vision pipeline** that ingests side-scan sonar (SSS) imagery, detects man-made debris — especially **ghost nets** (lost/abandoned fishing gear) — against a complex natural seafloor, and outputs **geotagged, actionable reports**.

Required components:

1. **Object detection / segmentation model** — bounding boxes (or masks) around man-made objects (shipwrecks, pipes, cylinders, entangled nets).
2. **Confidence scoring & noise filtering** — minimize false positives from natural shadows and rock clusters; output 0–100% confidence per detection.
3. **Anomaly reporting & geotagging engine** — read sonar metadata (coordinates / ping headers) and output structured JSON/CSV with lat/long, dimensions, classification per hazard.
4. **UI dashboard** — upload a sonar log, view detections overlaid on a map, download reports.

Stated challenges: high speckle noise, varying resolution, acoustic shadows, motion dropouts (heave/pitch/roll). Must run efficiently — **edge / marine-drone deployable, no heavy cloud dependency**.

**How SSS works (one line):** a towfish/AUV fires sound sideways across the seabed; each ping records echo brightness + slant distance, stacked into a 2D image. Objects are identified by their **brightness + acoustic shadow** (shadow length + sensor altitude → object height). Raw images need slant-range correction; a blind "nadir" strip sits under the sensor.

---

## 2. Honest Data Reality (do not violate)

- **There is NO public labeled ghost-net side-scan dataset.** Do not invent one or claim it exists.
- **Strategy:** prove the pipeline on rigid objects that *do* have real data; treat nets as an experimental class from synthetic data.
- **Primary dataset — SCTD:** side-scan, Pascal VOC (XML boxes), ~357 images. Classes: `ship` (271), `aircraft` (57), `human` (35), and a **junk class `ChaojieZhu` (57) that MUST be dropped** during conversion.
- **Pretraining/aux — KLSG:** real side-scan, but **classification format** (folders per class, no boxes): ship 385, plane 62.
- **Ghost-net class:** must come from **synthetic generation** (procedural or GAN). Be explicit that a synthetic-trained net detector learns the *synthetic* signature, not guaranteed to generalize to real nets, and that **net accuracy cannot be measured** without real net ground truth.

---

## 3. Solution Strategy

Do **not** promise "detect ghost nets" — promise **"separate man-made anomalies from natural seafloor,"** with nets as one experimental class. Report **measured accuracy (mAP) on real classes** (ship/aircraft/human); label the net class clearly as synthetic proof-of-concept.

**Differentiators (where the marks are — everyone builds detection + dashboard):**

1. **Shadow-based false-positive filter** — man-made objects cast geometric shadows; rocks cast jagged ones. Classical CV, near-zero compute (fits the edge constraint). Directly answers "reduce false positives from rocks/shadows."
2. **Real geo-referencing** — parse nav metadata, slant-range correct, convert pixel → lat/long. Most teams draw a box and stop.
3. **Honest data story** — transfer learning on real rigid objects + synthetic nets + augmentation.

Put ~60% of effort into these, not the model architecture.

---

## 4. Architecture

**Two separate pipelines.**

### Phase A — Training (offline, run once on GPU)

```
Real SSS data (SCTD boxes, KLSG pretraining) + Synthetic net images
        ↓ augmentation (speckle, dropouts, rotation, contrast)
        ↓ transfer-learn YOLOv8n from pretrained weights
        ↓ export
   trained weights (.pt / ONNX)   ← the only thing that carries into Phase B
```

### Phase B — Inference (the product)

```
INPUT: sonar file (.XTF) or image
 1. Parser              → image + nav metadata (GPS/heading/altitude per ping)
 2. Preprocessing       → speckle denoise · slant-range correction · nadir mask · normalize
 3. Detection (YOLOv8n) → boxes + class + raw score
 4. Shadow filter       → analyze shadow geometry → recalibrate confidence, drop false positives
 5. Geo-referencing     → pixel → across-track distance → lat/long · build acoustic map
 6. Report generator    → JSON/CSV (lat/long, dimensions, class, confidence)
 7. Dashboard           → overlay on map · download report
```

**"Acoustic map"** = the georeferenced seafloor image (sonar strips stitched onto real coordinates — a "sonar mosaic"). Building it = slant-range correction + placing pings at their GPS positions = the same work as geotagging. A single corrected, georeferenced strip with detection pins is enough for a demo.

**Design rules:** modular monolith (no microservices); the edge/no-cloud constraint justifies every choice (small YOLO, ONNX export, classical-CV shadow filter instead of a second neural net).

---

## 5. Tools & Links (per component)

| Component | Tool | Install | Link |
|---|---|---|---|
| Runtime | Python 3.10+ | — | https://www.python.org |
| Training env | Google Colab (T4 GPU) | — | https://colab.research.google.com |
| Detector | Ultralytics YOLOv8 | `pip install ultralytics` | https://github.com/ultralytics/ultralytics · docs: https://docs.ultralytics.com |
| DL framework | PyTorch | (bundled in Colab) | https://pytorch.org |
| Edge export/runtime | ONNX / ONNX Runtime | `pip install onnx onnxruntime` | https://onnxruntime.ai |
| Image/CV ops | OpenCV | `pip install opencv-python` | https://opencv.org |
| Filters (Lee/median) | scikit-image | `pip install scikit-image` | https://scikit-image.org |
| Numerics | NumPy | `pip install numpy` | https://numpy.org |
| Sonar file parser | pyxtf (XTF) | `pip install pyxtf` | https://github.com/oysstu/pyxtf |
| Coordinate transforms | pyproj | `pip install pyproj` | https://github.com/pyproj4/pyproj |
| Report tables | pandas | `pip install pandas` | https://pandas.pydata.org |
| Dashboard | Streamlit | `pip install streamlit` | https://streamlit.io |
| Map overlay | Folium (Leaflet) | `pip install folium` | https://python-visualization.github.io/folium |

### Dataset links

| Dataset | Link | Note |
|---|---|---|
| SCTD (primary) | https://github.com/freepoet/SCTD | side-scan, VOC boxes, drop `ChaojieZhu` |
| KLSG (pretraining) | https://github.com/huoguanying/SeabedObjects-Ship-and-Airplane-dataset | classification, no boxes |
| Roboflow SSS (YOLO-ready) | https://universe.roboflow.com/dae-hyeok-lee/side-scan-sonar | needs free account |
| Kaggle SSS Challenge | https://www.kaggle.com/competitions/side-scan-sonar-object-detection-challenge | needs account |
| SWDD (walls) | https://zenodo.org/records/13692547 | direct download |
| Marine-Debris-FLS | https://github.com/mvaldenegro/marine-debris-fls-datasets | forward-looking (wrong geometry) |
| OpenSonarDatasets (index) | https://github.com/remaro-network/OpenSonarDatasets | meta-repo |

---

## 6. Environment & Constraints

- **Train on GPU** (Colab T4 or Kaggle). Enable it: Runtime → Change runtime type → T4 GPU.
- **Train from LOCAL `/content` disk, never from mounted Google Drive** — Drive is network-mounted and bottlenecks the GPU on per-image reads.
- **Mount Drive only to persist** the converted dataset and trained weights (Colab wipes local disk on disconnect: idle ~90 min, 12 hr hard cap).
- **Real flow is 3 steps:** clone → unzip → convert VOC→YOLO → train. "Cloned" ≠ "training-ready."
- **Final model:** YOLOv8n, exported to ONNX, CPU-runnable at inference (no cloud).

---

## 7. Phase-by-Phase Build Order

**PHASE 1 — Data + Training (start here)**
1. Mount Google Drive (outputs only).
2. `git clone https://github.com/freepoet/SCTD.git`; unzip `SCTD.zip` (use the .zip, not the .rar).
3. Write `voc2yolo.py`: parse XML boxes, **drop `ChaojieZhu`**, remap remaining classes to 0..N, emit YOLO `.txt` labels + `data.yaml`, split train/val 80/20.
4. Keep prepared dataset on LOCAL `/content`.
5. `pip install ultralytics`; train YOLOv8n (`imgsz=640`, ~100 epochs) on GPU.
6. Save `best.pt` + `data.yaml` + converted dataset to Drive.
7. Print mAP; display a few validation predictions.

**PHASE 2 — Preprocessing (inference-time):** gentle speckle denoise (Lee/median — don't over-denoise, it erases thin net structures), slant-range correction, nadir masking, normalization.

**PHASE 3 — Detection + Shadow filter:** run YOLO; per detection, analyze acoustic shadow geometry (edge regularity/symmetry) to recalibrate confidence and reject rock/shadow false positives. Classical CV, not a second neural net.

**PHASE 4 — Geo-referencing + acoustic map:** if input carries nav metadata (XTF via pyxtf), convert detection pixel → across-track distance → lat/long (pyproj) and build a georeferenced map. **If no GPS metadata, say so and skip real coordinates — never fabricate them.**

**PHASE 5 — Report generator:** structured JSON + CSV per detection: lat/long, bounding dimensions, class, confidence.

**PHASE 6 — Dashboard (Streamlit):** upload sonar image → run pipeline → overlay detections + map pins → download report.

**PHASE X — Synthetic net generator (separate):** procedural OpenCV compositing (warped mesh/tangle filaments over sonar backgrounds) or a GAN, to bootstrap a `net` class. Label it experimental.

---

## 8. Rules for the Assistant

- Build one phase at a time; give runnable Colab cells; stop after each and give a verification step.
- Do not invent datasets or claim net data exists.
- Do not fabricate coordinates when GPS metadata is absent.
- Report accuracy only for classes with real ground truth; mark the net class as synthetic proof-of-concept.
- Keep it a modular monolith; justify tool choices against the edge/no-cloud constraint.

---

## 9. Deliverables Checklist

- [ ] `voc2yolo.py` — clean YOLO labels + `data.yaml` (junk class dropped)
- [ ] Trained `best.pt` + ONNX export (real GPU training, not smoke)
- [ ] `preprocess.py` — sonar-specific DSP
- [ ] `shadow_filter.py` — false-positive filter
- [ ] `geo.py` — pixel→lat/long + acoustic map
- [ ] `report.py` — JSON/CSV output
- [ ] `app.py` — Streamlit dashboard
- [ ] `synth_net.py` — synthetic net generator
- [ ] Reported mAP on real classes; net class labeled experimental

---

## 10. Honest Caveats (keep in your own head, and in the pitch)

- A trained model here detects **ship / aircraft / human** — not real ghost nets. The net story rests on synthetic data.
- Vibe-coding builds the pipeline, **not the accuracy** — real GPU training and data work are still on you.
- The `voc2yolo` conversion (class remap + coordinate math) is the first thing that breaks — verify Phase 1 actually trained.
- **Resolve two unknowns before investing further:** (1) how the hackathon is judged (working system vs raw accuracy), (2) whether they provide a dataset — if it includes real nets with GPS, the synthetic-net weakness disappears.
