"""Samudra Prahari — Streamlit Command Dashboard (UPGRADED).

Upload sonar strips → DSP preprocess → YOLO detect → shadow filter →
geo-anchor → interactive map → download JSON/CSV intelligence reports.

UPGRADES:
  - Lee filter denoising (preserves thin net structures)
  - Behind-box shadow scoring (solidity + regularity + contrast)
  - pyproj geodesic geo-referencing (proper WGS84 ellipsoid)
  - Physical dimensions in metres (from sonar resolution)
  - Full provenance in reports (yolo_conf, shadow_score, etc.)

Run:   streamlit run app.py
       ./run_dashboard.sh
"""
import streamlit as st
import cv2
import numpy as np
import pandas as pd
import json
import os
from PIL import Image

# Optional: Folium for interactive geo-maps
try:
    import folium
    from streamlit_folium import st_folium
    _HAS_FOLIUM = True
except ImportError:
    _HAS_FOLIUM = False

# --- Import upgraded pipeline modules ---
from preprocess import (
    gentle_median_filter, despeckle,
    mask_nadir, slant_range_correction,
    normalize_sonar
)
from shadow_filter import shadow_score, recalibrate
from geo_report import GeoReferencer
from acoustic_map_pipeline import create_acoustic_map_from_strips

# ---------------------------------------------------------------------------
# Page config & styling
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Samudra Prahari",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .reportview-container { background: #0E1117; }
    .main .block-container { padding-top: 2rem; }
    h1 { color: #00E5FF; font-family: 'Helvetica Neue', sans-serif; font-weight: 700; }
    .subtitle { color: #B0BEC5; font-size: 1.2rem; margin-bottom: 2rem; }
    .metric-card { background-color: #1E2329; border-radius: 10px; padding: 20px;
                   text-align: center; border: 1px solid #262730; }
    .metric-value { font-size: 2.5rem; font-weight: bold; color: #00E5FF; }
    .metric-label { color: #9E9E9E; font-size: 0.9rem; text-transform: uppercase;
                    letter-spacing: 1px; }
    .stButton>button { background-color: #00E5FF; color: black; font-weight: bold;
                       border-radius: 5px; border: none; padding: 10px 24px;
                       transition: all 0.3s ease; }
    .stButton>button:hover { background-color: #00B8D4;
                             box-shadow: 0 4px 8px rgba(0,229,255,0.3); }
</style>
""", unsafe_allow_html=True)

st.title("Samudra Prahari")
st.markdown(
    "<div class='subtitle'>AI-Powered Automated Underwater Marine Debris & Anomaly Detection System"
    "<br><span style='font-size:0.9rem; color:#00E5FF;'>"
    "Ministry of Earth Sciences (MoES) | NIOT | Problem Statement ID: 26057"
    "</span></div>",
    unsafe_allow_html=True
)

os.makedirs("outputs", exist_ok=True)
os.makedirs("temp_uploads", exist_ok=True)


# ---------------------------------------------------------------------------
# Detection class config
# ---------------------------------------------------------------------------

CLASS_COLORS_CV = {
    0: (0, 0, 255),    # Shipwreck: Red
    1: (255, 0, 0),    # Aircraft: Blue
    2: (0, 255, 255),  # Pipe: Yellow
    3: (255, 165, 0),  # Cylinder: Orange
    4: (0, 255, 0),    # Ghost Net: Green
}
CLASS_NAMES = ["Shipwreck", "Aircraft", "Pipe", "Cylinder", "Ghost Net"]

FOLIUM_COLORS = {
    "Shipwreck": "red", "Aircraft": "blue", "Pipe": "orange",
    "Cylinder": "purple", "Ghost Net": "green"
}


# ---------------------------------------------------------------------------
# Model loading (cached)
# ---------------------------------------------------------------------------

@st.cache_resource
def load_model(weights_path):
    from ultralytics import YOLO
    return YOLO(weights_path)


# ---------------------------------------------------------------------------
# Core processing: preprocess + detect + shadow filter for a single image
# ---------------------------------------------------------------------------

def process_single_image(img, model, enable_denoise, enable_nadir, enable_slant,
                         nadir_side="left", conf_thresh=0.15, keep_thresh=0.25):
    """Full pipeline on one image.

    Returns (preprocessed_img, list_of_detection_dicts, list_of_boxes_tuples).
    """
    # --- DSP Preprocessing ---
    if enable_denoise:
        img = gentle_median_filter(img)        # Lee filter (not median!)
    if enable_nadir:
        img = mask_nadir(img)
    if enable_slant:
        img = slant_range_correction(img)

    img = normalize_sonar(img)

    # --- YOLO Detection ---
    results = model(img, conf=conf_thresh, iou=0.4, verbose=False)

    # --- Shadow Filter + Recalibrate ---
    # Convert to grayscale for shadow analysis
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img

    detections = []
    boxes_tuples = []

    for r in results:
        for box in r.boxes:
            bx1, by1, bx2, by2 = map(int, box.xyxy[0])
            raw_conf = float(box.conf[0])
            cls_id = int(box.cls[0])
            cls_name = CLASS_NAMES[cls_id] if cls_id < len(CLASS_NAMES) else r.names[cls_id]

            # Shadow scoring: read the shadow BEHIND the box, not inside it
            bx = [bx1, by1, bx2, by2]
            score, shadow_dbg = shadow_score(gray, bx, nadir_side, cls_name=cls_name)
            cal_conf = recalibrate(raw_conf, score)

            # Geometric validation for elongated objects
            box_w, box_h = bx2 - bx1, by2 - by1
            aspect = max(box_w, box_h) / (min(box_w, box_h) + 1e-5)
            if cls_name in ("Pipe", "Cylinder"):
                if aspect < 1.15:
                    cal_conf *= 0.6
                else:
                    cal_conf *= 1.3
            cal_conf = min(1.0, cal_conf)

            if cal_conf >= keep_thresh:
                detections.append({
                    "class": cls_name,
                    "class_id": cls_id,
                    "box": [bx1, by1, bx2, by2],
                    "raw_conf": round(raw_conf, 4),
                    "shadow_score": round(score, 3),
                    "calibrated_conf": round(cal_conf, 4),
                    **shadow_dbg
                })
                boxes_tuples.append((bx1, by1, bx2, by2, cal_conf, cls_id))

    return img, detections, boxes_tuples


def draw_detections(img, boxes_tuples):
    """Draw bounding boxes and labels on the image."""
    vis = img.copy()
    for b in boxes_tuples:
        x1, y1, x2, y2, conf, cls_id = b
        color = CLASS_COLORS_CV.get(cls_id, (255, 255, 255))
        cls_name = CLASS_NAMES[cls_id] if cls_id < len(CLASS_NAMES) else f"cls_{cls_id}"

        # Physical dimensions in label
        label = f"{cls_name} {conf:.0%}"
        cv2.rectangle(vis, (x1, y1), (x2, y2), color, 3)
        y_label = y1 - 10 if y1 - 10 > 15 else y1 + 20
        cv2.putText(vis, label, (x1, y_label),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
    return vis


# ---------------------------------------------------------------------------
# Sidebar controls
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("Processing Engine")
    st.markdown("Toggle DSP algorithms applied before AI detection.")

    enable_stitching = st.checkbox(
        "Enable Acoustic Map Stitching", value=True,
        help="Stitches sequential strips into a continuous waterfall map."
    )

    stitch_direction = "Vertical"
    if enable_stitching:
        stitch_direction = st.radio(
            "Stitch Direction", ["Vertical", "Horizontal"],
            help="Vertical = end-to-end waterfall. Horizontal = side-by-side."
        )

    st.markdown("### DSP Toggles")
    enable_denoise = st.checkbox(
        "Speckle Denoise (Lee Filter)", value=True,
        help="Adaptive Lee filter: smooths noise, preserves thin net structures. "
             "Superior to median blur which erases thin lines."
    )
    enable_nadir = st.checkbox(
        "Nadir Masking", value=False,
        help="Zeros the central water-column band to prevent false detections."
    )
    enable_slant = st.checkbox(
        "Slant-Range Correction", value=False,
        help="Corrects geometric distortion from towfish altitude."
    )

    nadir_side = st.selectbox(
        "Nadir Side (for shadow analysis)", ["left", "right"],
        help="Which side of the image is the nadir/towfish. "
             "Shadows fall on the OPPOSITE side."
    )

    st.markdown("---")
    st.header("Geo-Anchoring Parameters")
    enable_geo = st.checkbox(
        "Enable Geo-Anchoring Mapping", value=False,
        help="Calculate physical lat/lon coordinates using geodesic math (pyproj)."
    )
    if enable_geo:
        st.markdown("Set towfish start coordinates and speed.")
        start_lat = st.number_input("Start Latitude", value=13.1000, format="%.4f")
        start_lon = st.number_input("Start Longitude", value=80.3000, format="%.4f")
        heading = st.number_input("Heading (degrees, 0=N)", value=0.0, format="%.1f")
        towfish_speed = st.slider(
            "Towfish Speed (knots)", min_value=1.0, max_value=5.0,
            value=3.0, step=0.1
        )
        resolution = st.number_input(
            "Resolution (m/px)", value=0.10, format="%.2f",
            help="Across-track metres per pixel. Derive from slant_range / sample_count."
        )
    else:
        start_lat, start_lon, heading = 13.10, 80.30, 0.0
        towfish_speed, resolution = 3.0, 0.10

    st.markdown("---")
    st.header("Model Settings")
    weights_path = st.text_input("Weights (.pt / .onnx)", "models/GhostNetSonar/best.pt")
    conf_thresh = st.slider("YOLO Confidence", 0.05, 0.90, 0.15, 0.05)
    keep_thresh = st.slider("Keep after Shadow Filter", 0.0, 0.90, 0.25, 0.05)


# ---------------------------------------------------------------------------
# File upload + processing
# ---------------------------------------------------------------------------

uploaded_files = st.file_uploader(
    "Upload Raw Sonar Strips (.jpg / .png)",
    type=["jpg", "jpeg", "png", "bmp", "tif", "tiff"],
    accept_multiple_files=True
)

if uploaded_files:
    if st.button("Generate Seamless Acoustic Map & Analyze"):

        # Load model once (cached)
        model = load_model(weights_path)

        # Save uploads and process each strip individually
        strip_paths = []
        individual_results = []

        for idx, file in enumerate(sorted(uploaded_files, key=lambda x: x.name)):
            p = os.path.join("temp_uploads", file.name)
            with open(p, "wb") as f:
                f.write(file.getbuffer())

            img = cv2.imread(p)
            if img is None:
                st.warning(f"Could not read {file.name}, skipping.")
                continue

            # Process: preprocess → detect → shadow filter
            processed_img, dets, boxes = process_single_image(
                img, model, enable_denoise, enable_nadir, enable_slant,
                nadir_side, conf_thresh, keep_thresh
            )

            # Overwrite temp file with preprocessed version (for stitcher)
            cv2.imwrite(p, processed_img)
            strip_paths.append(p)

            # Draw overlay
            vis = draw_detections(processed_img, boxes)

            # Per-strip geo report
            ind_geo = GeoReferencer(
                metadata_available=False,
                resolution_m_per_pixel=resolution,
                base_lat=start_lat if enable_geo else None,
                base_lon=start_lon if enable_geo else None,
                heading=heading,
                towfish_speed=towfish_speed
            )
            ind_h, ind_w = processed_img.shape[:2]
            ind_report = ind_geo.generate_report(
                dets, image_width=ind_w, image_height=ind_h,
                output_name=f"report_{file.name}"
            )

            individual_results.append({
                "name": file.name,
                "final_img": vis,
                "processed_img": processed_img,
                "boxes": boxes,
                "detections": dets,
                "report_data": ind_report
            })

        # --- Acoustic Map Stitching ---
        with st.status("Synthesizing Acoustic Map Pipeline...", expanded=True) as status:
            if enable_stitching and len(individual_results) > 1:
                st.write("Stitching preprocessed strips into Master Map...")

                # Stitch the annotated images
                final_map_images = []
                master_boxes = []
                master_dets = []
                current_offset = 0
                base_dim = None

                for res in individual_results:
                    img = res["final_img"]

                    if stitch_direction == "Vertical":
                        if base_dim is None:
                            base_dim = img.shape[1]
                        if img.shape[1] != base_dim:
                            img = cv2.resize(img, (base_dim, img.shape[0]))

                        final_map_images.append(img)
                        for b in res["boxes"]:
                            x1, y1, x2, y2, conf, cls_id = b
                            master_boxes.append(
                                (x1, y1 + current_offset, x2, y2 + current_offset,
                                 conf, cls_id)
                            )
                        for d in res["detections"]:
                            shifted = d.copy()
                            shifted["box"] = [
                                d["box"][0], d["box"][1] + current_offset,
                                d["box"][2], d["box"][3] + current_offset
                            ]
                            master_dets.append(shifted)
                        current_offset += img.shape[0]
                    else:
                        if base_dim is None:
                            base_dim = img.shape[0]
                        if img.shape[0] != base_dim:
                            img = cv2.resize(img, (img.shape[1], base_dim))

                        final_map_images.append(img)
                        for b in res["boxes"]:
                            x1, y1, x2, y2, conf, cls_id = b
                            master_boxes.append(
                                (x1 + current_offset, y1, x2 + current_offset, y2,
                                 conf, cls_id)
                            )
                        for d in res["detections"]:
                            shifted = d.copy()
                            shifted["box"] = [
                                d["box"][0] + current_offset, d["box"][1],
                                d["box"][2] + current_offset, d["box"][3]
                            ]
                            master_dets.append(shifted)
                        current_offset += img.shape[1]

                if stitch_direction == "Vertical":
                    final_map = cv2.vconcat(final_map_images)
                else:
                    final_map = cv2.hconcat(final_map_images)

                boxes = master_boxes

                # Master geo report
                st.write("Building Intelligence Report with geodesic math...")
                h, w = final_map.shape[:2]
                report_data = None

                geo = GeoReferencer(
                    metadata_available=False,
                    resolution_m_per_pixel=resolution,
                    base_lat=start_lat if enable_geo else None,
                    base_lon=start_lon if enable_geo else None,
                    heading=heading,
                    towfish_speed=towfish_speed
                )
                report_data = geo.generate_report(
                    master_dets, image_width=w, image_height=h,
                    output_name="master_acoustic_report"
                )

                cv2.imwrite("outputs/master_acoustic_map.jpg", final_map)

                st.session_state["acoustic_map_data"] = {
                    "final_map": final_map,
                    "boxes": boxes,
                    "report_data": report_data,
                    "w": w, "h": h,
                    "individual_results": individual_results,
                    "enable_geo": enable_geo
                }
            else:
                st.write("Showing individual analyses (stitching disabled or single image).")
                st.session_state["acoustic_map_data"] = {
                    "final_map": None,
                    "boxes": [],
                    "report_data": None,
                    "w": 0, "h": 0,
                    "individual_results": individual_results,
                    "enable_geo": enable_geo
                }

            status.update(label="Analysis Pipeline Complete!", state="complete",
                          expanded=False)


# ---------------------------------------------------------------------------
# Display results
# ---------------------------------------------------------------------------

if "acoustic_map_data" in st.session_state:
    data = st.session_state["acoustic_map_data"]
    final_map = data["final_map"]
    boxes = data["boxes"]
    report_data = data["report_data"]
    w, h = data["w"], data["h"]

    if final_map is not None:
        st.markdown("## Master Acoustic Mosaic")
        st.markdown("Sequential strips have been stitched into a continuous map. "
                     "Shadow-filtered detections are overlaid with calibrated confidence.")

        # Metric cards
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(
                f"<div class='metric-card'><div class='metric-value'>{len(boxes)}</div>"
                f"<div class='metric-label'>Debris Detected</div></div>",
                unsafe_allow_html=True
            )
        with col2:
            st.markdown(
                f"<div class='metric-card'><div class='metric-value'>{w}×{h}</div>"
                f"<div class='metric-label'>Mosaic Dimensions</div></div>",
                unsafe_allow_html=True
            )
        with col3:
            avg_conf = sum(b[4] for b in boxes) / len(boxes) if boxes else 0
            st.markdown(
                f"<div class='metric-card'><div class='metric-value'>{avg_conf:.0%}</div>"
                f"<div class='metric-label'>Avg Confidence</div></div>",
                unsafe_allow_html=True
            )
        with col4:
            avg_shadow = 0
            if report_data:
                scores = [d.get("shadow_score", 0) or 0 for d in report_data]
                avg_shadow = sum(scores) / len(scores) if scores else 0
            st.markdown(
                f"<div class='metric-card'><div class='metric-value'>{avg_shadow:.2f}</div>"
                f"<div class='metric-label'>Avg Shadow Score</div></div>",
                unsafe_allow_html=True
            )

        st.write("")

        # --- Tabs: Map + Geo ---
        if data.get("enable_geo") and _HAS_FOLIUM:
            tab1, tab2 = st.tabs(["Seamless Sonar Map", "Geo-Spatial Intelligence"])

            with tab1:
                st.image(cv2.cvtColor(final_map, cv2.COLOR_BGR2RGB),
                         caption="High-Resolution Annotated Sonar Mosaic",
                         use_container_width=True)

            with tab2:
                m = folium.Map(
                    location=[start_lat, start_lon], zoom_start=17,
                    tiles="CartoDB dark_matter"
                )

                # Towfish trackline
                try:
                    from pyproj import Geod
                    _g = Geod(ellps="WGS84")
                    track_len_m = h * resolution * (towfish_speed / 3.0)
                    end_lon, end_lat, _ = _g.fwd(start_lon, start_lat, heading, track_len_m)
                    folium.PolyLine(
                        [[start_lat, start_lon], [end_lat, end_lon]],
                        color="#00E5FF", weight=3, opacity=0.8,
                        tooltip="Towfish Trackline"
                    ).add_to(m)
                except ImportError:
                    length_m = h * resolution * (towfish_speed / 3.0)
                    end_lat = start_lat + (length_m * 0.000009)
                    folium.PolyLine(
                        [[start_lat, start_lon], [end_lat, start_lon]],
                        color="#00E5FF", weight=3, opacity=0.8,
                        tooltip="Towfish Trackline"
                    ).add_to(m)

                # Detection pins
                if report_data:
                    for d in report_data:
                        d_lat = d.get("lat")
                        d_lon = d.get("lon")
                        if d_lat is None or d_lon is None:
                            continue

                        popup = (
                            f"<b>Class:</b> {d['class']}<br>"
                            f"<b>Confidence:</b> {d['confidence']:.1%}<br>"
                            f"<b>Shadow Score:</b> {d.get('shadow_score', 'N/A')}<br>"
                            f"<b>Dimensions:</b> {d['bounding_dimensions_m']}<br>"
                            f"<b>YOLO Raw:</b> {d.get('yolo_conf', 'N/A')}"
                        )
                        pin_color = FOLIUM_COLORS.get(d["class"], "gray")
                        folium.Marker(
                            [d_lat, d_lon],
                            popup=popup,
                            icon=folium.Icon(color=pin_color, icon="info-sign")
                        ).add_to(m)

                st_folium(m, width=1200, height=600, key="interactive_geo_map")

        else:
            st.image(cv2.cvtColor(final_map, cv2.COLOR_BGR2RGB),
                     caption="High-Resolution Annotated Sonar Mosaic",
                     use_container_width=True)

        # --- Master Intelligence Report ---
        st.markdown("### Master Intelligence Report")
        if report_data:
            df = pd.DataFrame(report_data)
            # Highlight key columns
            display_cols = [
                "id", "class", "confidence_pct", "yolo_conf", "shadow_score",
                "bounding_dimensions_m", "width_m", "height_m",
                "lat", "lon", "across_track_m", "along_track_m"
            ]
            available = [c for c in display_cols if c in df.columns]
            st.dataframe(df[available], use_container_width=True)

            d_col1, d_col2 = st.columns(2)
            with d_col1:
                csv_path = "outputs/master_acoustic_report.csv"
                if os.path.exists(csv_path):
                    with open(csv_path, "r") as f:
                        st.download_button(
                            "Download Master CSV", f,
                            file_name="master_acoustic_report.csv",
                            mime="text/csv", use_container_width=True
                        )
            with d_col2:
                json_path = "outputs/master_acoustic_report.json"
                if os.path.exists(json_path):
                    with open(json_path, "r") as f:
                        st.download_button(
                            "Download Master JSON", f,
                            file_name="master_acoustic_report.json",
                            mime="application/json", use_container_width=True
                        )
        else:
            st.info("Enable Geo-Anchoring to generate coordinate reports.")

    else:
        st.info("Acoustic Map Stitching disabled or single image. "
                "See individual results below.")

    # --- Individual Image Breakdown ---
    st.markdown("---")
    st.markdown("## Individual Image Breakdown")
    st.markdown("Detailed AI analysis for each raw sonar strip uploaded.")

    if "individual_results" in data:
        for idx, res in enumerate(data["individual_results"]):
            n_debris = len(res["boxes"])
            with st.expander(
                f"Strip {idx+1}: {res['name']}  —  "
                f"{n_debris} debris item{'s' if n_debris != 1 else ''}"
            ):
                col_img, col_metrics = st.columns([2, 1])

                with col_img:
                    st.image(cv2.cvtColor(res["final_img"], cv2.COLOR_BGR2RGB),
                             use_container_width=True)

                with col_metrics:
                    for d in res.get("detections", []):
                        st.write(f"**{d['class']}** — Conf: {d['calibrated_conf']:.0%}")
                        st.write(f"  Raw YOLO: {d['raw_conf']:.2f} | "
                                 f"Shadow: {d['shadow_score']:.2f}")
                        bx = d["box"]
                        wpx = bx[2] - bx[0]
                        hpx = bx[3] - bx[1]
                        wm = round(wpx * resolution, 2)
                        hm = round(hpx * resolution, 2)
                        st.write(f"  Size: {wpx}×{hpx} px → **{wm}×{hm} m**")
                        st.write("---")

                    if not res.get("detections"):
                        st.write("No debris detected in this strip.")

                # Per-strip report table + downloads
                if res.get("report_data"):
                    st.markdown(f"#### Intelligence Report: {res['name']}")
                    ind_df = pd.DataFrame(res["report_data"])
                    display_cols = [
                        "id", "class", "confidence_pct", "shadow_score",
                        "bounding_dimensions_m", "width_m", "height_m"
                    ]
                    available = [c for c in display_cols if c in ind_df.columns]
                    st.dataframe(ind_df[available], use_container_width=True)

                    id_col1, id_col2 = st.columns(2)
                    csv_p = f"outputs/report_{res['name']}.csv"
                    json_p = f"outputs/report_{res['name']}.json"
                    with id_col1:
                        if os.path.exists(csv_p):
                            with open(csv_p, "r") as f:
                                st.download_button(
                                    "CSV", f,
                                    file_name=f"report_{res['name']}.csv",
                                    mime="text/csv", key=f"csv_{idx}",
                                    use_container_width=True
                                )
                    with id_col2:
                        if os.path.exists(json_p):
                            with open(json_p, "r") as f:
                                st.download_button(
                                    "JSON", f,
                                    file_name=f"report_{res['name']}.json",
                                    mime="application/json", key=f"json_{idx}",
                                    use_container_width=True
                                )
