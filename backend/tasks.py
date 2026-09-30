import os
import cv2
import json
import base64
import numpy as np
from celery_app import celery_app
from utils.storage import upload_file

# We need the V3 pipeline models
import sys
sys.path.append(os.path.abspath("."))
from src.pipeline.v3_pipeline import apply_v3_models

# And we need the V2 core YOLO pipeline
from src.pipeline.inference import load_model, process_single_image, draw_detections
from src.geo.geo_report import GeoReferencer
from database import SessionLocal, ProcessingHistory, Detection, UploadSession

# Load models globally in the worker
print("Loading YOLO Model...")
yolo_model = load_model("models/v3/yolo11n.onnx")
print("Models loaded successfully.")

@celery_app.task(bind=True, name="tasks.process_image_task")
def process_image_task(self, image_data_b64, filename, session_id, user_id, 
                      enable_denoise=True, enable_nadir=False, enable_slant=False,
                      nadir_side="left", conf_thresh=0.08, keep_thresh=0.15,
                      unet_thresh=0.3, enable_geo=False, start_lat=13.1, start_lon=80.3,
                      heading=0.0, towfish_speed=3.0, resolution=0.1):
                      
    img_bytes = base64.b64decode(image_data_b64)
    raw_url = upload_file(img_bytes, f"{session_id}/raw_{filename}", "image/jpeg")
    
    nparr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        return {"status": "error"}

    processed_img, dets, boxes = process_single_image(
        img, yolo_model, enable_denoise, enable_nadir, enable_slant,
        nadir_side, conf_thresh, keep_thresh
    )
    
    _, buf = cv2.imencode('.jpg', processed_img)
    processed_url = upload_file(buf.tobytes(), f"{session_id}/processed_{filename}")
    
    vis = draw_detections(processed_img, boxes)
    _, buf = cv2.imencode('.jpg', vis)
    vis_url = upload_file(buf.tobytes(), f"{session_id}/vis_{filename}")
    
    # V3 Pipeline Injection (U-Net & Heatmaps)
    v3_urls = apply_v3_models(img, filename, yolo_boxes=boxes, unet_thresh=unet_thresh)
    
    anomaly_url = None
    if v3_urls.get("anomaly_url"):
        with open("outputs/master_anomaly_map.jpg" if filename == "master_mosaic" else f"outputs/anomaly_{filename}", "rb") as f:
            anomaly_url = upload_file(f.read(), f"{session_id}/anomaly_{filename}")
            
    segmentation_url = None
    if v3_urls.get("segmentation_url"):
        with open("outputs/master_segmentation_map.jpg" if filename == "master_mosaic" else f"outputs/segmentation_{filename}", "rb") as f:
            segmentation_url = upload_file(f.read(), f"{session_id}/segmentation_{filename}")

    ind_h, ind_w = processed_img.shape[:2]
    ind_geo = GeoReferencer(
        metadata_available=False,
        resolution_m_per_pixel=resolution,
        base_lat=start_lat if enable_geo else None,
        base_lon=start_lon if enable_geo else None,
        heading=heading,
        towfish_speed=towfish_speed
    )
    ind_report = ind_geo.generate_report(dets, image_width=ind_w, image_height=ind_h, output_name=f"report_{filename}")

    # Database
    db = SessionLocal()
    try:
        skip_db = False
        if session_id:
            if not db.query(UploadSession).filter(UploadSession.id == session_id, UploadSession.user_id == user_id).first():
                skip_db = True
        
        if not skip_db:
            for d in ind_report:
                det = Detection(
                    filename=filename, class_name=d.get("class"), confidence=d.get("confidence_pct"),
                    lat=d.get("lat"), lon=d.get("lon"), width_m=d.get("width_m"), height_m=d.get("height_m"),
                    height_3d_m=d.get("height_3d_m"), shadow_score=d.get("shadow_score"),
                    user_id=user_id, session_id=session_id
                )
                db.add(det)
            
            max_conf = max([d.get("confidence_pct", 0.0) for d in ind_report]) if ind_report else 0.0
            hist = ProcessingHistory(
                filename=filename, uploaded_image_url=raw_url, processed_image_url=processed_url,
                map_stitching_output=vis_url, status="Pending", confidence=max_conf,
                report_data=json.dumps(ind_report), user_id=user_id, session_id=session_id
            )
            db.add(hist)
            db.commit()
    finally:
        db.close()

    # The exact format Viewer.tsx expects
    return {
        "status": "success",
        "name": filename,
        "width": ind_w,
        "height": ind_h,
        "detections": dets,
        "report_data": ind_report,
        "vis_url": vis_url,
        "processed_url": processed_url,
        "raw_url": raw_url,
        "anomaly_url": anomaly_url,
        "segmentation_url": segmentation_url
    }
