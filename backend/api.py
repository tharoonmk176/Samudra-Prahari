from concurrent.futures import ThreadPoolExecutor
import os
import cv2
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from typing import List

from src.pipeline.inference import load_model, process_single_image, draw_detections
from src.geo.geo_report import GeoReferencer
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker
import json
import threading

_api_model_lock = threading.Lock()
from src.pipeline.v3_pipeline import apply_v3_models
from src.processing.xtf_parser import xtf_to_images

Base = declarative_base()


import hashlib
import secrets
from fastapi import HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)

class UserSession(Base):
    __tablename__ = 'sessions'
    id = Column(Integer, primary_key=True, autoincrement=True)
    token = Column(String, unique=True, index=True)
    user_id = Column(Integer)

def get_current_user(token: str = Depends(oauth2_scheme)):
    session = SessionLocal()
    try:
        user_session = session.query(UserSession).filter(UserSession.token == token).first()
        if not user_session:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        user = session.query(User).filter(User.id == user_session.user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        return user
    finally:
        session.close()

from pydantic import BaseModel
class UserCreate(BaseModel):
    username: str
    password: str


class Detection(Base):
    __tablename__ = 'detections'
    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String)
    class_name = Column('class', String)
    confidence = Column(Float)
    lat = Column(Float)
    lon = Column(Float)
    width_m = Column(Float)
    height_m = Column(Float)
    height_3d_m = Column(Float)
    shadow_score = Column(Float)
    user_id = Column(Integer)
    session_id = Column(String)

class ImageModel(Base):
    __tablename__ = 'images'
    filename = Column(String, primary_key=True)
    user_id = Column(Integer, primary_key=True)
    status = Column(String)
    session_id = Column(String)

class ProcessingHistory(Base):
    __tablename__ = 'processing_history'
    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String)
    uploaded_image_url = Column(String)
    processed_image_url = Column(String)
    map_stitching_output = Column(String)
    status = Column(String)
    confidence = Column(Float)
    report_data = Column(String)
    user_id = Column(Integer)
    session_id = Column(String)
    is_video = Column(Boolean, default=False)

import uuid
import datetime

class UploadSession(Base):
    __tablename__ = 'upload_sessions'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String)
    created_at = Column(Float, default=lambda: datetime.datetime.now().timestamp())
    user_id = Column(Integer)


class UserPreferences(Base):
    __tablename__ = 'user_preferences'
    user_id = Column(Integer, primary_key=True)
    operator_id = Column(String, default="OPR-7729-DELTA")
    email = Column(String, default="operator.delta@samudra.sys")
    mfa_enabled = Column(Boolean, default=True)
    engine = Column(String, default="YOLO11n + UNet (Standard)")
    alert_threshold = Column(String, default="Medium (Confidence > 50%)")
    theme = Column(String, default="Deep Space Dark (Default)")
    auto_stitch = Column(Boolean, default=True)
    api_key = Column(String, default=lambda: "sk_live_" + secrets.token_hex(16))

import os
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///missions.db')
if DATABASE_URL.startswith('sqlite'):
    engine = create_engine(DATABASE_URL, connect_args={'timeout': 10.0})
else:
    engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

init_db()



from utils.storage import init_bucket
init_bucket()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("temp_uploads", exist_ok=True)
os.makedirs("outputs", exist_ok=True)

try:
    model = load_model("models/v3/yolo11n.onnx")
except Exception as e:
    print("Warning: Could not load model. Error:", e)
    model = None




from pydantic import BaseModel

class PrefsUpdate(BaseModel):
    operator_id: str
    email: str
    mfa_enabled: bool
    engine: str
    alert_threshold: str
    theme: str
    auto_stitch: bool

import shutil

def get_dir_size(path="outputs"):
    total = 0
    if os.path.exists(path):
        for dirpath, dirnames, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if not os.path.islink(fp):
                    total += os.path.getsize(fp)
    return total

@app.get("/preferences")
def get_preferences(current_user: User = Depends(get_current_user)):
    session = SessionLocal()
    try:
        prefs = session.query(UserPreferences).filter(UserPreferences.user_id == current_user.id).first()
        if not prefs:
            prefs = UserPreferences(user_id=current_user.id, api_key="sk_live_" + secrets.token_hex(16))
            session.add(prefs)
            session.commit()
            session.refresh(prefs)
            
        # Calculate real storage
        used_bytes = get_dir_size("outputs") + get_dir_size("temp_uploads")
        
        file_count = 0
        from pathlib import Path
        for directory in ["outputs", "temp_uploads"]:
            dir_path = Path(directory)
            if dir_path.exists():
                for f in dir_path.glob('**/*'):
                    if f.is_file():
                        file_count += 1
                        
        db_path = Path("missions.db")
        if db_path.exists():
            used_bytes += db_path.stat().st_size
            
        total_sessions = session.query(UploadSession).filter(UploadSession.user_id == current_user.id).count()
        total_detections = session.query(Detection).filter(Detection.user_id == current_user.id).count()

        # Let's say total quota is 10GB for this user
        total_quota = 10 * 1024 * 1024 * 1024 
        
        operator_display = prefs.operator_id
        if operator_display == "OPR-7729-DELTA":
            operator_display = current_user.username.upper()
        
        email_display = prefs.email
        if email_display == "operator.delta@samudra.sys":
            email_display = f"{current_user.username.lower()}@samudra.sys"

        return {
            "status": "success",
            "preferences": {
                "operator_id": operator_display,
                "email": email_display,
                "mfa_enabled": prefs.mfa_enabled,
                "engine": prefs.engine,
                "alert_threshold": prefs.alert_threshold,
                "theme": prefs.theme,
                "auto_stitch": prefs.auto_stitch,
                "api_key": getattr(prefs, 'api_key', "sk_live_" + secrets.token_hex(16)),
                "role": f"LEVEL 4 - {current_user.username.upper()}",
                "storage_used_bytes": used_bytes,
                "storage_total_bytes": total_quota,
                "db_sessions": total_sessions,
                "db_detections": total_detections,
                "file_count": file_count
            }
        }
    finally:
        session.close()

@app.post("/preferences")

def update_preferences(data: PrefsUpdate, current_user: User = Depends(get_current_user)):
    session = SessionLocal()
    try:
        prefs = session.query(UserPreferences).filter(UserPreferences.user_id == current_user.id).first()
        if not prefs:
            prefs = UserPreferences(user_id=current_user.id)
            session.add(prefs)
        
        prefs.operator_id = data.operator_id
        prefs.email = data.email
        prefs.mfa_enabled = data.mfa_enabled
        prefs.engine = data.engine
        prefs.alert_threshold = data.alert_threshold
        prefs.theme = data.theme
        prefs.auto_stitch = data.auto_stitch
        session.commit()
        return {"status": "success"}
    finally:
        session.close()

@app.post("/register")
def register(user: UserCreate):
    session = SessionLocal()
    try:
        if session.query(User).filter(User.username == user.username).first():
            raise HTTPException(status_code=400, detail="Username already registered")
        new_user = User(username=user.username, password_hash=hash_password(user.password))
        session.add(new_user)
        session.commit()
        return {"status": "success", "message": "User created successfully"}
    finally:
        session.close()

@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    session = SessionLocal()
    try:
        user = session.query(User).filter(User.username == form_data.username).first()
        if not user or user.password_hash != hash_password(form_data.password):
            raise HTTPException(status_code=400, detail="Incorrect username or password")
        token = secrets.token_hex(32)
        user_session = UserSession(token=token, user_id=user.id)
        session.add(user_session)
        session.commit()
        return {"access_token": token, "token_type": "bearer"}
    finally:
        session.close()

@app.get("/users/me")
def read_users_me(current_user: User = Depends(get_current_user)):
    return {"username": current_user.username, "id": current_user.id}

@app.post("/logout")
def logout(token: str = Depends(oauth2_scheme)):
    session = SessionLocal()
    try:
        session.query(UserSession).filter(UserSession.token == token).delete()
        session.commit()
        return {"status": "success"}
    finally:
        session.close()

@app.post("/sessions")
def create_session(name: str = Form("New Session"), current_user: User = Depends(get_current_user)):
    session = SessionLocal()
    try:
        new_sess = UploadSession(name=name, user_id=current_user.id)
        session.add(new_sess)
        session.commit()
        session.refresh(new_sess)
        return {"status": "success", "session": {"id": new_sess.id, "name": new_sess.name, "created_at": new_sess.created_at}}
    finally:
        session.close()

@app.get("/sessions")
def list_sessions(current_user: User = Depends(get_current_user)):
    session = SessionLocal()
    try:
        rows = session.query(UploadSession).filter(UploadSession.user_id == current_user.id).order_by(UploadSession.created_at.desc()).all()
        return {"status": "success", "sessions": [{"id": r.id, "name": r.name, "created_at": r.created_at} for r in rows]}
    finally:
        session.close()

@app.delete("/sessions/{session_id}")
def delete_session(session_id: str, current_user: User = Depends(get_current_user)):
    session = SessionLocal()
    try:
        sess = session.query(UploadSession).filter(UploadSession.id == session_id, UploadSession.user_id == current_user.id).first()
        if not sess:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session.query(ProcessingHistory).filter(ProcessingHistory.session_id == session_id, ProcessingHistory.user_id == current_user.id).delete()
        session.query(Detection).filter(Detection.session_id == session_id, Detection.user_id == current_user.id).delete()
        session.query(ImageModel).filter(ImageModel.session_id == session_id, ImageModel.user_id == current_user.id).delete()
        
        session.delete(sess)
        session.commit()
        return {"status": "success"}
    finally:
        session.close()

@app.post("/analyze")
async def analyze_strips(
    current_user: User = Depends(get_current_user),
    session_id: str = Form(None),
    files: List[UploadFile] = File(...),
    enable_denoise: str = Form("true"),
    enable_nadir: str = Form("false"),
    enable_slant: str = Form("false"),
    nadir_side: str = Form("left"),
    conf_thresh: float = Form(0.08),
    keep_thresh: float = Form(0.15),
    unet_thresh: float = Form(0.3),
    enable_geo: str = Form("false"),
    start_lat: float = Form(13.1),
    start_lon: float = Form(80.3),
    heading: float = Form(0.0),
    towfish_speed: float = Form(3.0),
    resolution: float = Form(0.1),
    weights_path: str = Form("models/v3/yolo11n.onnx")
):
    from celery import group
    import base64
    from celery_app import celery_app
    
    enable_denoise_bool = enable_denoise.lower() == "true"
    enable_nadir_bool = enable_nadir.lower() == "true"
    enable_slant_bool = enable_slant.lower() == "true"
    enable_geo_bool = enable_geo.lower() == "true"

    
    session_db = SessionLocal()
    try:
        prefs = session_db.query(UserPreferences).filter(UserPreferences.user_id == current_user.id).first()
        if prefs:
            if "High" in prefs.alert_threshold:
                conf_thresh = 0.8
            elif "All Detections" in prefs.alert_threshold:
                conf_thresh = 0.01
            if "Low Power" in prefs.engine:
                enable_denoise_bool = False
                enable_slant_bool = False
    finally:
        session_db.close()

    tasks = []
    for file in files:
        img_bytes = await file.read()
        b64 = base64.b64encode(img_bytes).decode('utf-8')
        
        sig = celery_app.signature("tasks.process_image_task", kwargs={
            "image_data_b64": b64,
            "filename": file.filename,
            "session_id": session_id,
            "user_id": current_user.id,
            "enable_denoise": enable_denoise_bool,
            "enable_nadir": enable_nadir_bool,
            "enable_slant": enable_slant_bool,
            "nadir_side": nadir_side,
            "conf_thresh": conf_thresh,
            "keep_thresh": keep_thresh,
            "unet_thresh": unet_thresh,
            "enable_geo": enable_geo_bool,
            "start_lat": start_lat,
            "start_lon": start_lon,
            "heading": heading,
            "towfish_speed": towfish_speed,
            "resolution": resolution
        })
        tasks.append(sig)
        
    print(f"Dispatching {len(tasks)} images to Celery workers...")
    job = group(tasks).apply_async()
    results = job.join() # Wait for all workers to finish
    print("All workers finished!")
    
    individual_results = []
    for r in results:
        if r and r.get("status") == "success":
            individual_results.append(r)
            
    return {"status": "success", "results": individual_results}

@app.post("/analyze_video")
async def analyze_video(
    current_user: User = Depends(get_current_user),
    session_id: str = Form(...),
    files: List[UploadFile] = File(...),
):
    global model
    if model is None:
        with _api_model_lock:
            if model is None:
                model = load_model("models/v3/yolo11n.onnx")

    files_sorted = sorted(files, key=lambda x: x.filename)
    os.makedirs("temp_uploads", exist_ok=True)
    os.makedirs("outputs", exist_ok=True)

    if len(files_sorted) == 1 and files_sorted[0].filename.endswith(".mp4"):
        raw_mp4_path = f"outputs/raw_video_{session_id}.mp4"
        with open(raw_mp4_path, "wb") as f:
            f.write(await files_sorted[0].read())
        cap = cv2.VideoCapture(raw_mp4_path)
        ret, first_frame = cap.read()
        if not ret:
            return {"status": "error", "message": "Could not read uploaded video"}
        h, w, _ = first_frame.shape
        cap.release()
    else:
        saved_paths = []
        for file in files_sorted:
            file_location = f"temp_uploads/{file.filename}"
            with open(file_location, "wb") as f:
                f.write(await file.read())
            saved_paths.append(file_location)
            
        if not saved_paths:
            return {"status": "error", "message": "No files provided"}
            
        first_frame = None
        w, h = 0, 0
        for path in saved_paths:
            first_frame = cv2.imread(path)
            if first_frame is not None:
                h, w, _ = first_frame.shape
                break
                
        if first_frame is None:
            return {"status": "error", "message": "Could not read any frames"}
        
        raw_mp4_path = f"outputs/raw_video_{session_id}.mp4"
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out_raw = cv2.VideoWriter(raw_mp4_path, fourcc, 10, (w, h))
        for path in saved_paths:
            frame = cv2.imread(path)
            if frame is not None:
                if frame.shape[:2] != (h, w):
                    frame = cv2.resize(frame, (w, h))
                out_raw.write(frame)
        out_raw.release()
        
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    cap = cv2.VideoCapture(raw_mp4_path)
    annotated_video_path = f"outputs/annotated_output_{session_id}.mp4"
    out_annotated = cv2.VideoWriter(annotated_video_path, fourcc, 10, (w, h))
    
    aggregated_dets = []
    individual_results = []
    frame_idx = 0
    
    # We must establish session_db here so we can save individual frames!
    session_db = SessionLocal()
    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            processed_img, dets, boxes = process_single_image(
                frame, model, True, False, False, "left", 0.08, 0.5
            )
            vis = draw_detections(processed_img, boxes)
            out_annotated.write(vis)
                
            frame_name = f"video_{session_id}_frame_{frame_idx}.jpg"
            cv2.imwrite(f"temp_uploads/{frame_name}", frame)
            cv2.imwrite(f"outputs/raw_{frame_name}", frame)
            cv2.imwrite(f"outputs/processed_{frame_name}", processed_img)
            cv2.imwrite(f"outputs/vis_{frame_name}", vis)
            
            yolo_boxes_extracted = boxes
            v3_urls = apply_v3_models(frame, frame_name, yolo_boxes=yolo_boxes_extracted, unet_thresh=0.3)
            
            ind_geo = GeoReferencer(
                metadata_available=False,
                resolution_m_per_pixel=0.1,
                base_lat=13.1,
                base_lon=80.3,
                heading=0,
                towfish_speed=3
            )
            ind_report = ind_geo.generate_report(dets, image_width=w, image_height=h, output_name=f"report_{frame_name}")
            
            hist_ind = ProcessingHistory(
                filename=frame_name,
                uploaded_image_url=f"/outputs/raw_{frame_name}",
                processed_image_url=f"/outputs/processed_{frame_name}",
                status="success",
                report_data=json.dumps(ind_report),
                user_id=current_user.id,
                session_id=session_id,
                is_video=False
            )
            session_db.add(hist_ind)
            if dets:
                aggregated_dets.extend(ind_report)
            
            individual_results.append({
                "name": frame_name,
                "width": w,
                "height": h,
                "detections": dets,
                "report_data": ind_report,
                "vis_url": f"/outputs/vis_{frame_name}",
                "processed_url": f"/outputs/processed_{frame_name}",
                "raw_url": f"/outputs/raw_{frame_name}",
                "anomaly_url": v3_urls["anomaly_url"],
                "segmentation_url": v3_urls["segmentation_url"],
            })
            frame_idx += 1
            
        cap.release()
        out_annotated.release()
        
        final_annotated_path = f"outputs/annotated_output_{session_id}_h264.mp4"
        import subprocess
        subprocess.run([
            "ffmpeg", "-y", "-i", annotated_video_path,
            "-vcodec", "libx264", "-acodec", "aac",
            final_annotated_path
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        hist = ProcessingHistory(
            filename=f"video_{session_id}",
            uploaded_image_url=f"/{raw_mp4_path}",
            processed_image_url=f"/{final_annotated_path}",
            status="success",
            report_data=json.dumps(aggregated_dets),
            user_id=current_user.id,
            session_id=session_id,
            is_video=True
        )
        session_db.add(hist)
        session_db.commit()
    finally:
        session_db.close()
        
    return {
        "status": "success", 
        "raw_video": f"/{raw_mp4_path}", 
        "annotated_video": f"/{final_annotated_path}",
        "is_video": True,
        "results": individual_results,
        "report_data": aggregated_dets
    }
@app.post("/stitch")
async def stitch_strips(
    current_user: User = Depends(get_current_user),
    session_id: str = Form(None),
    files: List[UploadFile] = File(...),
    stitch_direction: str = Form("Vertical"),
    enable_denoise: str = Form("true"),
    enable_nadir: str = Form("false"),
    enable_slant: str = Form("false"),
    nadir_side: str = Form("left"),
    conf_thresh: float = Form(0.08),
    keep_thresh: float = Form(0.15),
    unet_thresh: float = Form(0.3),
    enable_geo: str = Form("false"),
    start_lat: float = Form(13.1),
    start_lon: float = Form(80.3),
    heading: float = Form(0.0),
    towfish_speed: float = Form(3.0),
    resolution: float = Form(0.1),
    weights_path: str = Form("models/v3/yolo11n.onnx")
):
    
    session_db = SessionLocal()
    try:
        prefs = session_db.query(UserPreferences).filter(UserPreferences.user_id == current_user.id).first()
        if prefs:
            if "High" in prefs.alert_threshold:
                conf_thresh = 0.8
            elif "All Detections" in prefs.alert_threshold:
                conf_thresh = 0.01
            if "Low Power" in prefs.engine:
                enable_denoise_bool = False
                enable_slant_bool = False
    finally:
        session_db.close()

    global model, current_weights_path
    try:
        with _api_model_lock:
            if model is None or globals().get('current_weights_path') != weights_path:
                print("Loading YOLO model into RAM...")
                model = load_model(weights_path)
                globals()['current_weights_path'] = weights_path
    except Exception as e:
        print("Model load error:", e)

    enable_denoise_bool = enable_denoise.lower() == "true"
    enable_nadir_bool = enable_nadir.lower() == "true"
    enable_slant_bool = enable_slant.lower() == "true"
    enable_geo_bool = enable_geo.lower() == "true"

    individual_results = []
    
    file_bytes_list = []
    for file in files:
        file_bytes_list.append((file.filename, await file.read()))
        
    def process_file_worker(data):
        filename, file_bytes = data
        file_location = f"temp_uploads/{filename}"
        with open(file_location, "wb") as f:
            f.write(file_bytes)
            
        img = cv2.imread(file_location)
        if img is None: return None
            
        processed_img, dets, boxes = process_single_image(
            img, model, enable_denoise_bool, enable_nadir_bool, enable_slant_bool,
            nadir_side, conf_thresh, keep_thresh
        )
        cv2.imwrite(f"outputs/processed_{filename}", processed_img)
        vis = draw_detections(processed_img, boxes)
        cv2.imwrite(f"outputs/vis_{filename}", vis)
        
        v3_urls = apply_v3_models(img, filename, yolo_boxes=boxes, unet_thresh=unet_thresh)
        
        # Merge unknowns
        unknowns = v3_urls.get("unknown_boxes", [])
        for ub in unknowns:
            ux1, uy1, ux2, uy2 = ub
            # Check overlap with YOLO boxes
            overlap = False
            for yb in boxes:
                yx1, yy1, yx2, yy2, _, _ = yb
                # Simple intersection check
                if not (ux2 < yx1 or ux1 > yx2 or uy2 < yy1 or uy1 > yy2):
                    overlap = True
                    break
            
            if not overlap:
                # Calculate shadow score for volume
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
                from src.processing.shadow_filter import shadow_score
                score, shadow_dbg = shadow_score(gray, [ux1, uy1, ux2, uy2], nadir_side, cls_name="UNKNOWN DEBRIS")
                
                boxes.append((ux1, uy1, ux2, uy2, 0.99, 999)) # 999 is custom class
                dets.append({
                    "class": "UNKNOWN DEBRIS",
                    "class_id": 999,
                    "box": [ux1, uy1, ux2, uy2],
                    "raw_conf": 0.99,
                    "shadow_score": round(score, 3),
                    "calibrated_conf": 0.99,
                    **shadow_dbg
                })
                
        # Re-draw vis with new boxes
        vis = draw_detections(processed_img, boxes)
        cv2.imwrite(f"outputs/vis_{filename}", vis)
        
        ind_geo = GeoReferencer(
            metadata_available=False,
            resolution_m_per_pixel=resolution,
            base_lat=start_lat if enable_geo_bool else None,
            base_lon=start_lon if enable_geo_bool else None,
            heading=heading,
            towfish_speed=towfish_speed
        )
        ind_h, ind_w = processed_img.shape[:2]
        ind_report = ind_geo.generate_report(
            dets, image_width=ind_w, image_height=ind_h,
            output_name=f"report_{filename}"
        )
        
        import shutil
        shutil.copy(file_location, f"outputs/raw_{filename}")
        
        session_db = SessionLocal()
        try:
            for d in ind_report:
                det = Detection(
                    filename=filename,
                    class_name=d.get("class"),
                    confidence=d.get("confidence_pct"),
                    lat=d.get("lat"),
                    lon=d.get("lon"),
                    width_m=d.get("width_m"),
                    height_m=d.get("height_m"),
                    height_3d_m=d.get("height_3d_m"),
                    shadow_score=d.get("shadow_score"),
                    user_id=current_user.id,
                    session_id=session_id
                )
                session_db.add(det)
            
            max_conf = max([d.get("confidence_pct", 0.0) for d in ind_report]) if ind_report else 0.0
            hist = ProcessingHistory(
                filename=filename,
                uploaded_image_url=f"/outputs/raw_{filename}",
                processed_image_url=f"/outputs/processed_{filename}",
                map_stitching_output=None,
                status="Pending",
                confidence=max_conf,
                report_data=json.dumps(ind_report),
                user_id=current_user.id,
                session_id=session_id,
            )
            session_db.add(hist)
            session_db.commit()
        finally:
            session_db.close()
            
        return {
            "name": filename,
            "width": ind_w,
            "height": ind_h,
            "final_img": vis,
            "processed_img": processed_img,
            "boxes": boxes,
            "detections": dets,
            "report_data": ind_report,
            "vis_url": f"/outputs/vis_{filename}",
            "processed_url": f"/outputs/processed_{filename}",
            "raw_url": f"/outputs/raw_{filename}",
            "anomaly_url": v3_urls.get("anomaly_url"),
            "segmentation_url": v3_urls.get("segmentation_url")
        }
        
    with ThreadPoolExecutor(max_workers=4) as executor:
        results_list = list(executor.map(process_file_worker, file_bytes_list))
        
    for res in results_list:
        if res is not None:
            individual_results.append(res)

    if len(individual_results) <= 1:
        return {"status": "error", "message": "Need multiple strips to stitch"}

    final_map_images = []
    clean_map_images = []
    anomaly_map_images = []
    segmentation_map_images = []
    master_boxes = []
    master_dets = []
    current_offset = 0
    base_dim = None

    for res in individual_results:
        img = res["final_img"]
        clean_img = res["processed_img"]
        orig_h, orig_w = img.shape[:2]
        
        if stitch_direction == "Vertical":
            if base_dim is None:
                base_dim = orig_w
            
            scale_x = base_dim / orig_w
            if orig_w != base_dim:
                img = cv2.resize(img, (base_dim, orig_h))
                clean_img = cv2.resize(clean_img, (base_dim, orig_h))
                
            final_map_images.append(img)
            clean_map_images.append(clean_img)
            
            if res.get("anomaly_url"):
                ano_img = cv2.imread("outputs/" + res["anomaly_url"].split("/")[-1])
                if ano_img is not None:
                    if orig_w != base_dim: ano_img = cv2.resize(ano_img, (base_dim, orig_h))
                    anomaly_map_images.append(ano_img)
                    
            if res.get("segmentation_url"):
                seg_img = cv2.imread("outputs/" + res["segmentation_url"].split("/")[-1])
                if seg_img is not None:
                    if orig_w != base_dim: seg_img = cv2.resize(seg_img, (base_dim, orig_h))
                    segmentation_map_images.append(seg_img)
            
            for b in res["boxes"]:
                x1, y1, x2, y2, conf, cls_id = b
                master_boxes.append((int(x1 * scale_x), y1 + current_offset, int(x2 * scale_x), y2 + current_offset, conf, cls_id))
            for d in res["detections"]:
                shifted = d.copy()
                shifted["box"] = [int(d["box"][0] * scale_x), d["box"][1] + current_offset, int(d["box"][2] * scale_x), d["box"][3] + current_offset]
                master_dets.append(shifted)
            current_offset += orig_h
        else:
            if base_dim is None:
                base_dim = orig_h
                
            scale_y = base_dim / orig_h
            if orig_h != base_dim:
                img = cv2.resize(img, (orig_w, base_dim))
                clean_img = cv2.resize(clean_img, (orig_w, base_dim))
                
            final_map_images.append(img)
            clean_map_images.append(clean_img)
            
            if res.get("anomaly_url"):
                ano_img = cv2.imread("outputs/" + res["anomaly_url"].split("/")[-1])
                if ano_img is not None:
                    if orig_h != base_dim: ano_img = cv2.resize(ano_img, (orig_w, base_dim))
                    anomaly_map_images.append(ano_img)
                    
            if res.get("segmentation_url"):
                seg_img = cv2.imread("outputs/" + res["segmentation_url"].split("/")[-1])
                if seg_img is not None:
                    if orig_h != base_dim: seg_img = cv2.resize(seg_img, (orig_w, base_dim))
                    segmentation_map_images.append(seg_img)
            
            for b in res["boxes"]:
                x1, y1, x2, y2, conf, cls_id = b
                master_boxes.append((x1 + current_offset, int(y1 * scale_y), x2 + current_offset, int(y2 * scale_y), conf, cls_id))
            for d in res["detections"]:
                shifted = d.copy()
                shifted["box"] = [d["box"][0] + current_offset, int(d["box"][1] * scale_y), d["box"][2] + current_offset, int(d["box"][3] * scale_y)]
                master_dets.append(shifted)
            current_offset += orig_w

    if stitch_direction == "Vertical":
        final_map = cv2.vconcat(final_map_images)
        clean_map = cv2.vconcat(clean_map_images)
        if anomaly_map_images and len(anomaly_map_images) == len(final_map_images):
            cv2.imwrite("outputs/master_anomaly_map.jpg", cv2.vconcat(anomaly_map_images))
        if segmentation_map_images and len(segmentation_map_images) == len(final_map_images):
            cv2.imwrite("outputs/master_segmentation_map.jpg", cv2.vconcat(segmentation_map_images))
    else:
        final_map = cv2.hconcat(final_map_images)
        clean_map = cv2.hconcat(clean_map_images)
        if anomaly_map_images and len(anomaly_map_images) == len(final_map_images):
            cv2.imwrite("outputs/master_anomaly_map.jpg", cv2.hconcat(anomaly_map_images))
        if segmentation_map_images and len(segmentation_map_images) == len(final_map_images):
            cv2.imwrite("outputs/master_segmentation_map.jpg", cv2.hconcat(segmentation_map_images))

    cv2.imwrite("outputs/master_acoustic_map.jpg", final_map)
    cv2.imwrite("outputs/master_clean_map.jpg", clean_map)
    
    h, w = final_map.shape[:2]
    geo = GeoReferencer(
        metadata_available=False,
        resolution_m_per_pixel=resolution,
        base_lat=start_lat if enable_geo_bool else None,
        base_lon=start_lon if enable_geo_bool else None,
        heading=heading,
        towfish_speed=towfish_speed
    )
    report_data = geo.generate_report(master_dets, image_width=w, image_height=h, output_name="master_acoustic_report")
    

    # Save to SQLite Database
    session_db = SessionLocal()
    try:
        skip_db = False
        if session_id:
            if not session_db.query(UploadSession).filter(UploadSession.id == session_id, UploadSession.user_id == current_user.id).first():
                skip_db = True
        if not skip_db:
            for d in report_data:
                det = Detection(
                    filename="master_mosaic",
                    class_name=d.get("class"),
                    confidence=d.get("confidence_pct"),
                    lat=d.get("lat"),
                    lon=d.get("lon"),
                    width_m=d.get("width_m"),
                    height_m=d.get("height_m"),
                    height_3d_m=d.get("height_3d_m"),
                    shadow_score=d.get("shadow_score"),
                    user_id=current_user.id,
                    session_id=session_id,
                )
                session_db.add(det)
                
            max_conf = max([d.get("confidence_pct", 0.0) for d in report_data]) if report_data else 0.0
            hist = ProcessingHistory(
                filename="master_mosaic",
                uploaded_image_url=None,
                processed_image_url="/outputs/master_clean_map.jpg",
                map_stitching_output="/outputs/master_acoustic_map.jpg",
                status="Pending",
                confidence=max_conf,
                report_data=json.dumps(report_data),
                user_id=current_user.id,
                session_id=session_id
            )
            session_db.add(hist)
            session_db.commit()
    finally:
        session_db.close()

    # Remove cv2 images before returning JSON
    for res in individual_results:
        res.pop("final_img", None)
        res.pop("processed_img", None)
        
    return {
        "status": "success", 
        "master_map_url": "/outputs/master_acoustic_map.jpg",
        "master_clean_url": "/outputs/master_clean_map.jpg",
        "master_anomaly_url": "/outputs/master_anomaly_map.jpg" if os.path.exists("outputs/master_anomaly_map.jpg") else None,
        "master_segmentation_url": "/outputs/master_segmentation_map.jpg" if os.path.exists("outputs/master_segmentation_map.jpg") else None,
        "report_data": report_data,
        "width": w,
        "height": h,
        "individual_results": individual_results
    }


@app.post("/clear_history")
def clear_history(session_id: str = Form(None), current_user: User = Depends(get_current_user)):
    session = SessionLocal()
    try:
        if session_id:
            session.query(Detection).filter(Detection.user_id == current_user.id, Detection.session_id == session_id).delete()
            session.query(ProcessingHistory).filter(ProcessingHistory.user_id == current_user.id, ProcessingHistory.session_id == session_id).delete()
            session.query(ImageModel).filter(ImageModel.user_id == current_user.id, ImageModel.session_id == session_id).delete()
        else:
            session.query(Detection).filter(Detection.user_id == current_user.id).delete()
            session.query(ProcessingHistory).filter(ProcessingHistory.user_id == current_user.id).delete()
            session.query(ImageModel).filter(ImageModel.user_id == current_user.id).delete()
        session.commit()
    finally:
        session.close()
    return {"status": "success"}

@app.get("/processing_history")
def get_processing_history(session_id: str = None, current_user: User = Depends(get_current_user)):
    session = SessionLocal()
    try:
        query = session.query(ProcessingHistory).filter(ProcessingHistory.user_id == current_user.id)
        if session_id:
            query = query.filter(ProcessingHistory.session_id == session_id)
        rows = query.order_by(ProcessingHistory.id.desc()).all()
        data = []
        for r in rows:
            report_data = []
            try:
                if r.report_data:
                    report_data = json.loads(r.report_data)
            except:
                pass
                
            w, h = 0, 0
            img_path = r.map_stitching_output or r.processed_image_url
            if img_path:
                local_path = img_path.lstrip("/")
                if os.path.exists(local_path):
                    import cv2
                    img = cv2.imread(local_path)
                    if img is not None:
                        h, w = img.shape[:2]
            
            anomaly_url = f"/outputs/anomaly_{r.filename}" if r.filename != "master_mosaic" else "/outputs/master_anomaly_map.jpg"
            if not os.path.exists(anomaly_url.lstrip("/")): anomaly_url = None
            
            segmentation_url = f"/outputs/segmentation_{r.filename}" if r.filename != "master_mosaic" else "/outputs/master_segmentation_map.jpg"
            if not os.path.exists(segmentation_url.lstrip("/")): segmentation_url = None

            data.append({
                "id": r.id,
                "filename": r.filename,
                "uploaded_image_url": r.uploaded_image_url,
                "processed_image_url": r.processed_image_url,
                "map_stitching_output": r.map_stitching_output,
                "status": r.status,
                "confidence": r.confidence,
                "report_data": report_data,
                "width": w,
                "height": h,
                "anomaly_url": anomaly_url,
                "segmentation_url": segmentation_url,
                "session_id": r.session_id,
                "is_video": getattr(r, "is_video", False)
            })
    finally:
        session.close()
    return {"status": "success", "history": data}

@app.get("/history")
def get_history(session_id: str = None, current_user: User = Depends(get_current_user)):
    session = SessionLocal()
    try:
        query = session.query(Detection, ImageModel.status).outerjoin(ImageModel, (Detection.filename == ImageModel.filename) & (ImageModel.user_id == current_user.id)).filter(Detection.user_id == current_user.id)
        if session_id:
            query = query.filter(Detection.session_id == session_id)
        results = query.order_by(Detection.id.desc()).all()
        data = []
        for det, status in results:
            data.append({
                "id": det.id,
                "filename": det.filename,
                "class": det.class_name,
                "confidence": det.confidence,
                "lat": det.lat,
                "lon": det.lon,
                "width_m": det.width_m,
                "height_m": det.height_m,
                "height_3d_m": det.height_3d_m,
                "shadow_score": det.shadow_score,
                "image_status": status or "Pending"
            })
    finally:
        session.close()
    return {"status": "success", "history": data}

@app.post("/update_status")
async def update_status(filename: str = Form(...), status: str = Form(...), current_user: User = Depends(get_current_user)):
    session = SessionLocal()
    try:
        img = session.query(ImageModel).filter(ImageModel.filename == filename, ImageModel.user_id == current_user.id).first()
        if img:
            img.status = status
        else:
            img = ImageModel(filename=filename, user_id=current_user.id, status=status)
            session.add(img)
            
        session.query(ProcessingHistory).filter(ProcessingHistory.filename == filename, ProcessingHistory.user_id == current_user.id).update({"status": status})
        session.commit()
    finally:
        session.close()

    # Update reports
    if filename == "master_mosaic":
        json_path = "outputs/master_acoustic_report.json"
        csv_path = "outputs/master_acoustic_report.csv"
    else:
        json_path = f"outputs/report_{filename}.json"
        csv_path = f"outputs/report_{filename}.csv"
    
    if os.path.exists(json_path):
        import csv
        with open(json_path, "r") as f:
            data = json.load(f)
        
        data["image_status"] = status
        for det in data.get("detections", []):
            det["image_status"] = status
            
        with open(json_path, "w") as f:
            json.dump(data, f, indent=4)
            
        if data.get("detections"):
            keys = list(data["detections"][0].keys())
            with open(csv_path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                writer.writerows(data["detections"])

    return {"status": "success"}

from fastapi.staticfiles import StaticFiles
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
