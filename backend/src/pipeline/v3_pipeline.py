import cv2
import numpy as np
import onnxruntime as ort
import threading

ae_session = None
unet_session = None
_model_lock = threading.Lock()

def init_onnx_models():
    global ae_session, unet_session
    with _model_lock:
        try:
            if not ae_session:
                sess_options = ort.SessionOptions()
                sess_options.intra_op_num_threads = 4
                ae_session = ort.InferenceSession('models/v3/stage_a_ae.onnx', sess_options, providers=['TensorrtExecutionProvider', 'CUDAExecutionProvider', 'CPUExecutionProvider'])
        except:
            pass

def apply_v3_models(img, filename, yolo_boxes=None, unet_thresh=0.5):
    init_onnx_models()
    
    original_h, original_w = img.shape[:2]
    img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Auto-calculate optimal background suppression threshold dynamically based on the image's acoustic histogram
    # Combine Otsu with the static slider for a hybrid threshold
    dyn_thresh_val, _ = cv2.threshold(img_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    dynamic_thresh = (dyn_thresh_val / 255.0) * unet_thresh
    
    squashed_img = cv2.resize(img_gray, (640, 640))
    tensor_1ch = squashed_img.astype(np.float32) / 255.0
    tensor_1ch = np.expand_dims(np.expand_dims(tensor_1ch, axis=0), axis=0)
    
    urls = {}
    
    if ae_session:
        ae_out = ae_session.run(None, {'input': tensor_1ch})[0]
        ano_tile = np.abs(tensor_1ch[0, 0] - ae_out[0, 0])
        full_anomaly_map = cv2.resize(ano_tile, (original_w, original_h))
        err_mean = np.mean(full_anomaly_map)
        err_p99 = np.percentile(full_anomaly_map, 99.9) + 1e-5
        shifted = np.clip(full_anomaly_map - err_mean, 0, None)
        normalized_err = np.clip(shifted / (err_p99 - err_mean), 0, 1)
        normalized_err = np.power(normalized_err, 0.3)
        heatmap = cv2.applyColorMap(np.uint8(255 * normalized_err), cv2.COLORMAP_JET)
        out_path = f"outputs/anomaly_{filename}"
        cv2.imwrite(out_path, heatmap)
        urls["anomaly_url"] = f"/{out_path}"
        
    blended = img.copy()
    has_segmentation = False
    boxes_to_segment = yolo_boxes if yolo_boxes is not None else []
    
    # FLAWLESS REVERSE THERMAL ENGINE (GAUSSIAN FADE)
    if len(boxes_to_segment) > 0:
        for box in boxes_to_segment:
            x1, y1, x2, y2 = [int(v) for v in box[:4]]
            
            # 15% Padding to let the thermal glow breathe
            w, h = x2 - x1, y2 - y1
            px, py = int(w * 0.15), int(h * 0.15)
            x1 = max(0, x1 - px)
            y1 = max(0, y1 - py)
            x2 = min(original_w, x2 + px)
            y2 = min(original_h, y2 + py)
            
            if x2 <= x1 or y2 <= y1:
                continue

            # 1. Create a 2D Gaussian Bell Curve centered precisely on the YOLO object
            bw, bh = x2 - x1, y2 - y1
            cx, cy = bw / 2, bh / 2
            x_range = np.arange(bw)
            y_range = np.arange(bh)
            xx, yy = np.meshgrid(x_range, y_range)
            
            # Calculate 2D Gaussian (1.0 at center, fading to 0.0 at edges)
            sigma_x, sigma_y = bw / 4.0, bh / 4.0
            gaussian = np.exp(-(((xx - cx)**2) / (2 * sigma_x**2) + ((yy - cy)**2) / (2 * sigma_y**2)))
            gaussian = gaussian.astype(np.float32)

            # 2. Extract Sonar Texture to map the physical ridges
            roi_gray = img_gray[y1:y2, x1:x2]
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
            enhanced = clahe.apply(roi_gray).astype(np.float32) / 255.0
            
            # CLASSIC GAUSSIAN FADE
            roi_alpha = gaussian * enhanced
            roi_alpha[roi_alpha < dynamic_thresh] = 0
            roi_alpha = np.clip(roi_alpha * 2.5, 0, 0.95)
            
            # 3. Apply the Reverse Color Gradient
            dark_purple = np.array([60, 0, 60], dtype=np.float32)
            light_purple = np.array([255, 100, 255], dtype=np.float32)
            
            color_overlay = np.zeros_like(blended[y1:y2, x1:x2], dtype=np.float32)
            for c in range(3):
                # Center (gaussian=1) is dark, edges (gaussian=0) are light
                color_overlay[:, :, c] = (1.0 - gaussian) * light_purple[c] + gaussian * dark_purple[c]
                
            roi_alpha_3ch = np.dstack([roi_alpha]*3)
            blended[y1:y2, x1:x2] = (blended[y1:y2, x1:x2].astype(np.float32) * (1.0 - roi_alpha_3ch) + color_overlay * roi_alpha_3ch).astype(np.uint8)

            has_segmentation = True

    if has_segmentation:
        cv2.imwrite(f"outputs/segmentation_{filename}", blended)
        urls["segmentation_url"] = f"/outputs/segmentation_{filename}"
    else:
        cv2.imwrite(f"outputs/segmentation_{filename}", img)
        urls["segmentation_url"] = f"/outputs/segmentation_{filename}"
        
    urls["unknown_boxes"] = []
    return urls
