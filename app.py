import streamlit as st
import cv2
import numpy as np
import pandas as pd
import json
import os
from PIL import Image
import folium
from streamlit_folium import st_folium

# Import our modular pipeline components
from preprocess import gentle_median_filter, mask_nadir, slant_range_correction, normalize_sonar
from shadow_filter import run_phase3
import importlib
import geo_report
importlib.reload(geo_report)
from geo_report import GeoReferencer
import acoustic_map_pipeline
importlib.reload(acoustic_map_pipeline)
from acoustic_map_pipeline import create_acoustic_map_from_strips, detect_on_acoustic_map

st.set_page_config(
    page_title="Samudra Prahari",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CUSTOM CSS FOR A PREMIUM LOOK ---
st.markdown("""
<style>
    .reportview-container { background: #0E1117; }
    .main .block-container { padding-top: 2rem; }
    h1 { color: #00E5FF; font-family: 'Helvetica Neue', sans-serif; font-weight: 700; }
    .subtitle { color: #B0BEC5; font-size: 1.2rem; margin-bottom: 2rem; }
    .metric-card { background-color: #1E2329; border-radius: 10px; padding: 20px; text-align: center; border: 1px solid #262730; }
    .metric-value { font-size: 2.5rem; font-weight: bold; color: #00E5FF; }
    .metric-label { color: #9E9E9E; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 1px; }
    .stButton>button { background-color: #00E5FF; color: black; font-weight: bold; border-radius: 5px; border: none; padding: 10px 24px; transition: all 0.3s ease; }
    .stButton>button:hover { background-color: #00B8D4; box-shadow: 0 4px 8px rgba(0,229,255,0.3); }
</style>
""", unsafe_allow_html=True)

st.title("Samudra Prahari")
st.markdown("<div class='subtitle'>AI-Powered Automated Underwater Marine Debris & Anomaly Detection System<br><span style='font-size:0.9rem; color:#00E5FF;'>Ministry of Earth Sciences (MoES) | NIOT | Problem Statement ID: 26057</span></div>", unsafe_allow_html=True)

os.makedirs("outputs", exist_ok=True)
os.makedirs("temp_uploads", exist_ok=True)

with st.sidebar:
    st.header("Processing Engine")
    st.markdown("Toggle which DSP algorithms to apply to the raw sonar data before AI detection.")
    enable_stitching = st.checkbox("Enable Acoustic Map Stitching", value=True, help="Stitches sequential overlapping strips into a continuous waterfall map.")
    
    stitch_direction = "Vertical"
    if enable_stitching:
        stitch_direction = st.radio("Stitch Direction", ["Vertical", "Horizontal"], help="Vertical stacks strips end-to-end (like a continuous waterfall). Horizontal places them side-by-side.")
        
    enable_denoise = st.checkbox("Enable Speckle Denoise", value=False, help="Applies gentle median filtering to reduce acoustic speckle noise.")
    enable_nadir = st.checkbox("Enable Nadir Masking", value=False, help="Masks the central water-column nadir artifact.")
    enable_slant = st.checkbox("Enable Slant-Range Correction", value=False, help="Corrects geometric distortion from towfish altitude.")
    
    st.markdown("---")
    st.header("Geo-Anchoring Parameters")
    enable_geo = st.checkbox("Enable Geo-Anchoring Mapping", value=False, help="Calculate physical lat/long coordinates and generate an interactive web map.")
    if enable_geo:
        st.markdown("Set the starting coordinates and speed of the towfish to mathematically stretch a GPS grid across the acoustic mosaic.")
        start_lat = st.number_input("Start Latitude", value=33.4000, format="%.4f")
        start_lon = st.number_input("Start Longitude", value=-118.3000, format="%.4f")
        towfish_speed = st.slider("Towfish Speed (knots)", min_value=1.0, max_value=5.0, value=3.0, step=0.1)
    else:
        start_lat, start_lon, towfish_speed = 33.4, -118.3, 3.0
    
uploaded_files = st.file_uploader("Upload Raw Sonar Strips (.jpg/.png) or .ZIP", type=["jpg", "jpeg", "png", "bmp", "zip"], accept_multiple_files=True)

if uploaded_files:
    if st.button("Generate Seamless Acoustic Map & Analyze"):
        st.session_state["analysis_results"] = []
        
        # Save uploaded files sequentially
        strip_paths = []
        individual_results = []
        for idx, file in enumerate(sorted(uploaded_files, key=lambda x: x.name)):
            p = os.path.join("temp_uploads", file.name)
            with open(p, "wb") as f:
                f.write(file.getbuffer())
            strip_paths.append(p)
            
            # --- PROCESS INDIVIDUAL IMAGE ---
            from ultralytics import YOLO
            ind_img = cv2.imread(p)
            
            # Apply Selected DSP Preprocessing
            if enable_denoise: ind_img = gentle_median_filter(ind_img)
            if enable_nadir: ind_img = mask_nadir(ind_img)
            if enable_slant: ind_img = slant_range_correction(ind_img)
            
            # Overwrite the temp file with the preprocessed version so the stitcher uses the clean data
            cv2.imwrite(p, ind_img)
            
            model = YOLO("models/GhostNetSonar/best.pt")
            ind_results = model(ind_img, conf=0.25, iou=0.4, verbose=False)
            
            ind_boxes = []
            ind_final = ind_img.copy()
            for r in ind_results:
                for box in r.boxes:
                    bx1, by1, bx2, by2 = map(int, box.xyxy[0])
                    conf = float(box.conf[0])
                    cls_id = int(box.cls[0])
                    ind_boxes.append((bx1, by1, bx2, by2, conf, cls_id))
                    
            colors = {0: (0, 0, 255), 1: (255, 0, 0), 2: (0, 255, 255), 3: (255, 165, 0), 4: (0, 255, 0)}
            names = ['Shipwreck', 'Aircraft', 'Pipe', 'Cylinder', 'Ghost Net']
            for b in ind_boxes:
                x1, y1, x2, y2, conf, cls_id = b
                color = colors.get(cls_id, (255, 255, 255))
                label = f"{names[cls_id]} {conf:.2f}"
                cv2.rectangle(ind_final, (x1, y1), (x2, y2), color, 3)
                cv2.putText(ind_final, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
                
            ind_formatted_detections = []
            for b in ind_boxes:
                ind_formatted_detections.append({
                    "class": names[b[5]],
                    "class_id": b[5],
                    "box": [b[0], b[1], b[2], b[3]],
                    "calibrated_conf": b[4]
                })
            
            ind_geo = GeoReferencer(
                metadata_available=False,
                resolution_m_per_pixel=0.1,
                base_lat=start_lat if enable_geo else None,
                base_lon=start_lon if enable_geo else None,
                towfish_speed=towfish_speed if enable_geo else 3.0
            )
            ind_h, ind_w = ind_img.shape[:2]
            ind_report_data = ind_geo.generate_report(ind_formatted_detections, image_width=ind_w, image_height=ind_h, output_name=f"report_{file.name}")
                
            individual_results.append({
                "name": file.name,
                "final_img": ind_final,
                "boxes": ind_boxes,
                "report_data": ind_report_data
            })
            
        with st.status("Synthesizing Acoustic Map Pipeline...", expanded=True) as status:
            if enable_stitching and len(individual_results) > 1:
                st.write("Stitching Individual Analyses into Master Map...")
                
                final_map_images = []
                master_boxes = []
                current_offset = 0
                base_dim = None
                
                for res in individual_results:
                    img = res["final_img"]
                    
                    if stitch_direction == "Vertical":
                        if base_dim is None: base_dim = img.shape[1]
                        if img.shape[1] != base_dim:
                            img = cv2.resize(img, (base_dim, img.shape[0]))
                            
                        final_map_images.append(img)
                        for b in res["boxes"]:
                            x1, y1, x2, y2, conf, cls_id = b
                            master_boxes.append((x1, y1 + current_offset, x2, y2 + current_offset, conf, cls_id))
                        current_offset += img.shape[0]
                    else:
                        if base_dim is None: base_dim = img.shape[0]
                        if img.shape[0] != base_dim:
                            img = cv2.resize(img, (img.shape[1], base_dim))
                            
                        final_map_images.append(img)
                        for b in res["boxes"]:
                            x1, y1, x2, y2, conf, cls_id = b
                            master_boxes.append((x1 + current_offset, y1, x2 + current_offset, y2, conf, cls_id))
                        current_offset += img.shape[1]
                
                if stitch_direction == "Vertical":
                    final_map = cv2.vconcat(final_map_images)
                else:
                    final_map = cv2.hconcat(final_map_images)
                    
                boxes = master_boxes
                
                st.write("Building Intelligence Report...")
                h, w = final_map.shape[:2]
                report_data = None
                
                if enable_geo:
                    formatted_detections = []
                    class_names = ['Shipwreck', 'Aircraft', 'Pipe', 'Cylinder', 'Ghost Net']
                    for b in boxes:
                        formatted_detections.append({
                            "class": class_names[b[5]],
                            "class_id": b[5],
                            "box": [b[0], b[1], b[2], b[3]],
                            "calibrated_conf": b[4]
                        })
                        
                    geo = GeoReferencer(
                        metadata_available=False, 
                        resolution_m_per_pixel=0.1,
                        base_lat=start_lat,
                        base_lon=start_lon,
                        towfish_speed=towfish_speed
                    )
                    report_data = geo.generate_report(formatted_detections, image_width=w, image_height=h, output_name="master_acoustic_report")
                
                mosaic_out_path = "outputs/master_acoustic_map.jpg"
                cv2.imwrite(mosaic_out_path, final_map)
                
                st.session_state["acoustic_map_data"] = {
                    "final_map": final_map,
                    "boxes": boxes,
                    "report_data": report_data,
                    "w": w,
                    "h": h,
                    "individual_results": individual_results,
                    "enable_geo": enable_geo
                }
            else:
                st.write("Acoustic Map Stitching disabled. Showing individual analyses only.")
                st.session_state["acoustic_map_data"] = {
                    "final_map": None,
                    "boxes": [],
                    "report_data": None,
                    "w": 0,
                    "h": 0,
                    "individual_results": individual_results
                }
            status.update(label="Analysis Pipeline Complete!", state="complete", expanded=False)
            
# --- DISPLAY ---
if "acoustic_map_data" in st.session_state:
    data = st.session_state["acoustic_map_data"]
    final_map = data["final_map"]
    boxes = data["boxes"]
    report_data = data["report_data"]
    w, h = data["w"], data["h"]
    
    if final_map is not None:
        st.markdown("## Master Acoustic Mosaic")
        st.markdown("The overlapping strips have been perfectly stitched via FFT Phase Correlation, eliminating distortion. The Ultimate YOLOv8 model analyzed the giant mosaic using a sliding mathematical window.")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"<div class='metric-card'><div class='metric-value'>{len(boxes)}</div><div class='metric-label'>Debris Detected</div></div>", unsafe_allow_html=True)
        with col2:
            st.markdown(f"<div class='metric-card'><div class='metric-value'>{w} x {h}</div><div class='metric-label'>Mosaic Dimensions</div></div>", unsafe_allow_html=True)
        with col3:
            avg_conf = sum(b[4] for b in boxes) / len(boxes) if boxes else 0
            st.markdown(f"<div class='metric-card'><div class='metric-value'>{avg_conf:.1%}</div><div class='metric-label'>Avg Model Confidence</div></div>", unsafe_allow_html=True)
            
        st.write("")
        
        if data.get("enable_geo", True):
            tab1, tab2 = st.tabs(["Seamless Sonar Map", "Geo-Spatial Intelligence"])
            
            with tab1:
                st.image(cv2.cvtColor(final_map, cv2.COLOR_BGR2RGB), caption="High-Resolution Annotated Sonar Mosaic", use_container_width=True)
                
            with tab2:
                base_lat, base_lon = start_lat, start_lon
                interactive_map = folium.Map(location=[base_lat, base_lon], zoom_start=17, tiles="CartoDB dark_matter")
                
                length_m = h * 0.1 * (towfish_speed / 3.0) 
                end_lat = base_lat + (length_m * 0.000009)
                folium.PolyLine([[base_lat, base_lon], [end_lat, base_lon]], color="#00E5FF", weight=3, opacity=0.8, tooltip="Towfish Trackline").add_to(interactive_map)
                
                if report_data:
                    for d in report_data:
                        d_lat = base_lat + (d["along_track_m"] * 0.000009)
                        d_lon = base_lon + (d["across_track_m"] * 0.000009)
                        
                        popup_text = f"<b>Class:</b> {d['class']}<br><b>Conf:</b> {d['confidence']:.2%}<br><b>Dims:</b> {d['bounding_dimensions_m']}"
                        
                        colors = {"Shipwreck": "red", "Aircraft": "blue", "Pipe": "orange", "Cylinder": "purple", "Ghost Net": "green"}
                        pin_color = colors.get(d['class'], "gray")
                        
                        folium.Marker(
                            [d_lat, d_lon],
                            popup=popup_text,
                            icon=folium.Icon(color=pin_color, icon="info-sign")
                        ).add_to(interactive_map)
                        
                st_folium(interactive_map, width=1200, height=600, key="interactive_geo_map")
                
            st.markdown("### Master Intelligence Report")
            if report_data:
                df = pd.DataFrame(report_data)
                st.dataframe(df, use_container_width=True)
                
                d_col1, d_col2 = st.columns(2)
                with d_col1:
                    with open("outputs/master_acoustic_report.csv", "r") as f:
                        st.download_button("Download Master CSV", f, file_name="master_acoustic_report.csv", mime="text/csv", use_container_width=True)
                with d_col2:
                    with open("outputs/master_acoustic_report.json", "r") as f:
                        st.download_button("Download Master JSON", f, file_name="master_acoustic_report.json", mime="application/json", use_container_width=True)
        else:
            st.image(cv2.cvtColor(final_map, cv2.COLOR_BGR2RGB), caption="High-Resolution Annotated Sonar Mosaic", use_container_width=True)
    else:
        st.info("Acoustic Map Stitching was disabled or insufficient images were provided. Showing individual results below.")

    st.markdown("---")
    st.markdown("## Individual Image Breakdown")
    st.markdown("Detailed AI analysis for each raw sonar strip uploaded.")
    
    if "individual_results" in data:
        for idx, res in enumerate(data["individual_results"]):
            with st.expander(f"Strip {idx+1}: {res['name']} ({len(res['boxes'])} debris items)"):
                col_img, col_metrics = st.columns([2, 1])
                with col_img:
                    st.image(cv2.cvtColor(res['final_img'], cv2.COLOR_BGR2RGB), use_container_width=True)
                with col_metrics:
                    for b in res['boxes']:
                        x1, y1, x2, y2, conf, cls_id = b
                        names = ['Shipwreck', 'Aircraft', 'Pipe', 'Cylinder', 'Ghost Net']
                        st.write(f"**{names[cls_id]}** (Conf: {conf:.1%})")
                        st.write(f"Coords: [{x1}, {y1}] to [{x2}, {y2}]")
                        st.write("---")
                
                if res.get("report_data"):
                    st.markdown(f"#### Intelligence Report: {res['name']}")
                    ind_df = pd.DataFrame(res["report_data"])
                    st.dataframe(ind_df, use_container_width=True)
                    
                    id_col1, id_col2 = st.columns(2)
                    with id_col1:
                        with open(f"outputs/report_{res['name']}.csv", "r") as f:
                            st.download_button(f"Download CSV", f, file_name=f"report_{res['name']}.csv", mime="text/csv", key=f"csv_{idx}", use_container_width=True)
                    with id_col2:
                        with open(f"outputs/report_{res['name']}.json", "r") as f:
                            st.download_button(f"Download JSON", f, file_name=f"report_{res['name']}.json", mime="application/json", key=f"json_{idx}", use_container_width=True)
