"""Detection + Acoustic-Shadow False-Positive Filter — UPGRADED.

Run YOLO, then for each box read the ACOUSTIC SHADOW BEHIND it (far-from-nadir
side).  A man-made object throws a clean, regular, constant-width shadow; a rock
throws a jagged/incoherent one; noise throws none.  We score the shadow geometry
and recalibrate confidence — classical CV, no second neural net.

Shadow score in [0,1] from three cues:
  solidity      — area / convex-hull-area  (regular outline → 1)
  regularity    — constant width down the shadow  (rigid object → 1)
  contrast      — the shadow is actually dark vs surrounding seabed

Ghost nets get INVERTED scoring: their shadows should be broken and chaotic,
so high complexity / low solidity is a POSITIVE signal for nets.

Recalibrated conf = yolo_conf × (floor + (1−floor) × score).
"""
import cv2
import numpy as np
import os

# Heuristic weights — hand-tuned.  Fit a tiny logistic on labelled shadows
# if you ever get ground truth; until then these are the calibration knobs.
W_SOLIDITY, W_REGULARITY, W_CONTRAST = 0.5, 0.3, 0.2
MIN_CONTRAST = 0.15           # below this the "shadow" is just seabed → no real shadow
SHADOW_LEVEL = 0.6            # shadow = pixels below this fraction of the seabed median


# ---------------------------------------------------------------------------
# Core shadow analysis
# ---------------------------------------------------------------------------

def _shadow_strip(gray, box, nadir_side, shadow_len):
    """Extract the strip of seabed where the shadow should fall.

    The shadow is cast on the OPPOSITE side from the nadir (sound source).
    """
    x1, y1, x2, y2 = (int(v) for v in box)
    h, w = gray.shape[:2]
    L = shadow_len or (x2 - x1)                       # shadow ≈ object size by default

    if nadir_side == "left":                           # object lit from left → shadow right
        sx1, sx2 = x2, min(w, x2 + L)
    else:                                              # nadir on the right → shadow left
        sx1, sx2 = max(0, x1 - L), x1

    return gray[max(0, y1):min(h, y2), sx1:sx2]


def shadow_score(gray, box, nadir_side="left", shadow_len=None, cls_name="unknown"):
    """Return (score in [0,1], debug dict) for the shadow behind `box`.

    `gray` must be the FULL grayscale image (not a crop), so we can read
    the shadow strip adjacent to the bounding box.
    """
    # Convert to grayscale if BGR
    if len(gray.shape) == 3:
        gray = cv2.cvtColor(gray, cv2.COLOR_BGR2GRAY)

    strip = _shadow_strip(gray, box, nadir_side, shadow_len)
    dbg = {"solidity": 0.0, "regularity": 0.0, "contrast": 0.0}

    if strip.size < 20:
        return 0.0, dict(dbg, reason="strip too small")

    # Seabed reference: global median (robust even when the shadow fills the strip)
    ref = float(np.median(gray))
    dark = (strip.astype(np.float32) < SHADOW_LEVEL * ref).astype(np.uint8) * 255
    cnts, _ = cv2.findContours(dark, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not cnts:
        return 0.15, dict(dbg, reason="no dark region")

    c = max(cnts, key=cv2.contourArea)
    area = cv2.contourArea(c)
    if area < 10 or area / strip.size < 0.05:
        return 0.2, dict(dbg, reason="shadow too small")

    # Contrast: how much darker is the shadow than the seabed?
    mask = np.zeros(strip.shape[:2], np.uint8)
    cv2.drawContours(mask, [c], -1, 255, -1)
    shadow_mean = float(strip[mask > 0].mean()) if len(strip.shape) == 2 else float(cv2.cvtColor(strip, cv2.COLOR_BGR2GRAY)[mask > 0].mean())
    contrast = np.clip((ref - shadow_mean) / (ref + 1e-6), 0, 1)
    if contrast < MIN_CONTRAST:
        return 0.2, dict(dbg, contrast=float(contrast), reason="no contrast")

    # Solidity: how convex is the shadow? (1 = clean rectangle, low = ragged)
    hull = cv2.contourArea(cv2.convexHull(c))
    solidity = area / (hull + 1e-6)

    # Regularity: how constant is the shadow width across rows?
    widths = (mask > 0).sum(axis=1)
    widths = widths[widths > 0]
    regularity = 1.0 / (1.0 + widths.std() / (widths.mean() + 1e-6))

    # --- Class-specific scoring ---
    if cls_name in ("ghost_net", "Ghost Net", "net"):
        # Ghost nets cast CHAOTIC, broken shadows — invert the scoring
        # Low solidity + low regularity = GOOD for a net
        chaos = (1.0 - solidity) * 0.5 + (1.0 - regularity) * 0.3 + contrast * 0.2
        score = float(np.clip(chaos, 0, 1))
        # Boost if it looks properly chaotic
        if solidity < 0.70 or regularity < 0.50:
            score = min(1.0, score * 1.2)
    else:
        # Rigid objects: clean shadow = high score
        score = float(np.clip(
            W_SOLIDITY * solidity + W_REGULARITY * regularity + W_CONTRAST * contrast,
            0, 1
        ))

    return score, {
        "solidity": round(solidity, 3),
        "regularity": round(regularity, 3),
        "contrast": round(float(contrast), 3)
    }


def recalibrate(conf, score, floor=0.4):
    """Blend YOLO confidence with shadow evidence.  floor = min fraction kept."""
    return float(conf * (floor + (1 - floor) * score))


# ---------------------------------------------------------------------------
# Backward-compatible wrapper
# ---------------------------------------------------------------------------

def analyze_shadow(crop_img, cls_name="unknown", full_img=None, box=None, nadir_side="left"):
    """Wrapper for backward compatibility.

    If full_img and box are provided, uses the proper behind-box shadow analysis.
    Otherwise falls back to analyzing the crop (less accurate but still functional).
    """
    if full_img is not None and box is not None:
        score, _ = shadow_score(full_img, box, nadir_side, cls_name=cls_name)
        return min(1.0, max(0.1, score))

    # Legacy fallback: analyze shadow within the crop
    if len(crop_img.shape) == 3:
        gray = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)
    else:
        gray = crop_img

    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return 0.3

    c = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(c)
    if area < 20:
        return 0.5

    hull_area = cv2.contourArea(cv2.convexHull(c))
    if hull_area == 0:
        return 0.5

    solidity = area / hull_area
    perimeter = cv2.arcLength(c, True)
    complexity = (perimeter ** 2) / (area + 1e-5)

    if cls_name in ("ghost_net", "Ghost Net", "net"):
        if complexity > 30 or solidity < 0.70:
            return min(1.0, 1.2)
        return 0.8
    else:
        if solidity < 0.65 or complexity > 40:
            return 0.4
        elif solidity > 0.85:
            return min(1.0, 1.1)
        return 1.0


# ---------------------------------------------------------------------------
# Standalone detection pipeline
# ---------------------------------------------------------------------------

def detect_with_shadow(img, model, nadir_side="left", keep=0.25, conf_thresh=0.15):
    """Full pipeline: YOLO → shadow recalibrate → filter.

    Takes a loaded YOLO model and an image array (BGR).
    Returns (list of detection dicts, annotated image).
    """
    from preprocess import preprocess_array

    # Preprocess
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
    pre = preprocess_array(gray)
    pre_bgr = cv2.cvtColor(pre, cv2.COLOR_GRAY2BGR) if len(pre.shape) == 2 else pre

    # Detect
    results = model(pre_bgr, conf=conf_thresh, verbose=False)

    out = []
    for r in results:
        for box in r.boxes:
            bx = box.xyxy[0].tolist()
            raw_conf = float(box.conf)
            cls_id = int(box.cls)
            cls_name = r.names[cls_id]

            # Shadow scoring on the full preprocessed image
            score, dbg = shadow_score(pre, bx, nadir_side, cls_name=cls_name)
            cal_conf = recalibrate(raw_conf, score)

            # Geometric validation for elongated objects
            bw, bh = bx[2] - bx[0], bx[3] - bx[1]
            aspect = max(bw, bh) / (min(bw, bh) + 1e-5)
            geo_penalty = 1.0
            if cls_name in ("pipe", "Pipe", "cylinder", "Cylinder"):
                if aspect < 1.15:
                    geo_penalty = 0.6
                else:
                    geo_penalty = 1.3
            cal_conf *= geo_penalty

            if cal_conf >= keep:
                out.append({
                    "class": cls_name,
                    "class_id": cls_id,
                    "box": [round(v, 1) for v in bx],
                    "raw_conf": round(raw_conf, 3),
                    "shadow_score": round(score, 3),
                    "calibrated_conf": round(cal_conf, 3),
                    **dbg
                })

    return out, pre


def run_phase3(img_path, model_path="models/GhostNetSonar/best.onnx",
               out_path="outputs/phase3_output.jpg", conf_thresh=0.15):
    """Execute the Detection + Shadow Filter pipeline from file."""
    from ultralytics import YOLO

    img = cv2.imread(img_path)
    if img is None:
        raise ValueError(f"Could not load {img_path}")

    model = YOLO(model_path)
    dets, pre = detect_with_shadow(img, model, conf_thresh=conf_thresh)

    # Draw results
    vis = cv2.cvtColor(pre, cv2.COLOR_GRAY2BGR) if len(pre.shape) == 2 else pre.copy()
    for d in dets:
        x1, y1, x2, y2 = (int(v) for v in d["box"])
        color = (0, 255, 0) if d["shadow_score"] >= 0.5 else (0, 165, 255)
        cv2.rectangle(vis, (x1, y1), (x2, y2), color, 2)
        label = f"{d['class']}: {d['calibrated_conf']:.2f} (raw: {d['raw_conf']:.2f})"
        y_label = y1 - 10 if y1 - 10 > 15 else y1 + 20
        cv2.putText(vis, label, (x1, y_label), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    os.makedirs(os.path.dirname(out_path) if os.path.dirname(out_path) else ".", exist_ok=True)
    cv2.imwrite(out_path, vis)
    print(f"Phase 3 complete! {len(dets)} detections. Saved to {out_path}")

    return dets


# ---------------------------------------------------------------------------
# Self-check
# ---------------------------------------------------------------------------

def demo():
    """Self-check: clean shadow scores higher than jagged; no shadow scores low."""
    rng = np.random.default_rng(0)

    def _synth(kind):
        img = np.clip(rng.normal(140, 12, (90, 220)), 0, 255).astype(np.uint8)
        img[30:60, 30:55] = 235                                # object echo
        if kind == "clean":
            img[30:60, 55:120] = 12                            # neat rectangle shadow
        elif kind == "jagged":
            for r in range(30, 60):
                img[r, 55:55 + rng.integers(8, 60)] = 12      # ragged shadow
        return img, (30, 30, 55, 60)

    scores = {}
    for kind in ("clean", "jagged", "none"):
        img, box = _synth(kind)
        scores[kind], dbg = shadow_score(img, box, "left")
        print(f"  {kind:6s} score={scores[kind]:.3f} {dbg}")

    assert scores["clean"] > 0.55, scores
    assert scores["clean"] > scores["jagged"], scores
    assert scores["none"] < 0.35, scores
    assert recalibrate(0.9, scores["clean"]) > recalibrate(0.9, scores["none"])
    print("shadow_filter demo OK")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--img")
    p.add_argument("--weights", default="models/GhostNetSonar/best.pt")
    p.add_argument("--out", default="outputs/phase3_output.jpg")
    p.add_argument("--demo", action="store_true")
    a = p.parse_args()

    if a.demo:
        demo()
    elif a.img:
        run_phase3(a.img, a.weights, a.out)
    else:
        print("Usage: python shadow_filter.py --img <path> [--weights <path>] [--demo]")
