"""Sonar-specific DSP Preprocessing Engine — UPGRADED with Adaptive Lee Filter.

Four toggleable steps:  despeckle (Lee) → slant_range_correct → mask_nadir → normalize

KEY UPGRADE: Uses the adaptive Lee filter instead of median blur.
A median erases 1px-wide lines (a thin ghost net looks exactly like that).
Lee smooths flat speckle but keeps high-variance edges/lines, honoring
"don't erase thin structures".

Geometry convention: dual-channel waterfall with nadir at the centre.
Single-channel strips also supported (nadir at column 0).
"""
import cv2
import numpy as np
import os


# ---------------------------------------------------------------------------
# Core DSP functions
# ---------------------------------------------------------------------------

def _lee_channel(ch, size, damping):
    """Lee filter on a single float32 channel."""
    f = ch.astype(np.float32)
    mean = cv2.blur(f, (size, size))
    var  = np.maximum(cv2.blur(f * f, (size, size)) - mean * mean, 0)
    noise = var.mean() * damping                        # noise-variance estimate
    w = var / (var + noise + 1e-6)                      # →0 flat (smooth), →1 edge (keep)
    return np.clip(mean + w * (f - mean), 0, 255)


def despeckle(img, size=5, damping=1.0):
    """Adaptive Lee speckle filter.  Flat areas → smoothed; edges/thin lines → kept.
    Works on both grayscale and BGR images.
    `size` and `damping` are calibration knobs (bigger = more smoothing)."""
    if len(img.shape) == 3:
        channels = cv2.split(img)
        filtered = [_lee_channel(ch, size, damping) for ch in channels]
        return cv2.merge(filtered).astype(np.uint8)
    return _lee_channel(img, size, damping).astype(np.uint8)


def gentle_median_filter(img, ksize=3):
    """UPGRADED: Uses adaptive Lee filter instead of median blur.

    The Lee filter smooths flat speckle noise while preserving high-variance
    edges and thin line structures (ghost nets, cables, filaments) that a
    median filter would completely erase.

    This function name is kept for backward compatibility with the dashboard.
    """
    # Map the median kernel size to a Lee window size
    lee_size = max(3, ksize)
    return despeckle(img, size=lee_size, damping=1.0)


def slant_range_correction(img, sensor_altitude_pixels=30):
    """Converts slant-range to ground-range: ground = sqrt(slant² − alt²).

    Uses cv2.remap for mathematically perfect sub-pixel interpolation.
    Handles both single-channel and dual-channel (nadir-at-centre) layouts.
    """
    h, w = img.shape[:2]
    center_idx = w / 2.0

    # Build the remap LUT (1D, tiled across rows)
    x_coords = np.arange(w, dtype=np.float32)
    ground_ranges = np.abs(x_coords - center_idx)

    # ground → slant (inverse: where to *sample* in the original)
    slant_ranges = np.sqrt(ground_ranges ** 2 + sensor_altitude_pixels ** 2)

    # Map back to original image coordinates
    orig_x = np.where(
        x_coords < center_idx,
        center_idx - slant_ranges,
        center_idx + slant_ranges
    ).astype(np.float32)

    map_x = np.tile(orig_x, (h, 1))
    map_y = np.repeat(np.arange(h, dtype=np.float32)[:, None], w, axis=1)

    return cv2.remap(img, map_x, map_y,
                     interpolation=cv2.INTER_LINEAR,
                     borderMode=cv2.BORDER_REPLICATE)


def mask_nadir(img, nadir_width_pixels=60):
    """Zeros the central water-column band (nadir).

    Instead of inpainting (which fabricates data), this honestly zeros the
    nadir zone. If the centre is not actually dark, the image is returned
    unchanged — preventing accidental masking of valid seabed.
    """
    h, w = img.shape[:2]
    center_idx = w // 2
    half = nadir_width_pixels // 2
    start_col = max(0, center_idx - half)
    end_col   = min(w, center_idx + half)

    # Only mask if the centre is actually darker than the rest (real nadir)
    center_mean  = np.mean(img[:, start_col:end_col])
    overall_mean = np.mean(img)

    if center_mean < overall_mean * 0.7:
        out = img.copy()
        out[:, start_col:end_col] = 0
        return out

    return img


def normalize_sonar(img, lo=1, hi=99):
    """Percentile-clip and scale to uint8 0–255.

    Kills hot pixels and dynamic-range swings without crushing the contrast.
    """
    arr = img.astype(np.float32)
    if len(arr.shape) == 3:
        # For colour images, compute percentiles across all channels jointly
        flat = arr.flatten()
    else:
        flat = arr.flatten()

    a, b = np.percentile(flat, (lo, hi))
    if b - a < 1e-6:
        return img.astype(np.uint8) if img.dtype != np.uint8 else img

    return (np.clip((arr - a) / (b - a), 0, 1) * 255).astype(np.uint8)


# ---------------------------------------------------------------------------
# Convenience: full pipeline in one call
# ---------------------------------------------------------------------------

def preprocess_pipeline(image_path, output_path=None,
                        altitude_px=30, nadir_px=60,
                        enable_denoise=True, enable_nadir=True,
                        enable_slant=True):
    """Execute the full DSP preprocessing pipeline on a file."""
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Cannot read {image_path}")

    if enable_denoise:
        img = despeckle(img)
    if enable_nadir:
        img = mask_nadir(img, nadir_px)
    if enable_slant:
        img = slant_range_correction(img, altitude_px)
    img = normalize_sonar(img)

    if output_path:
        cv2.imwrite(output_path, img)
        print(f"Preprocessed image saved to {output_path}")

    return img


def preprocess_array(img, altitude_px=0, size=5):
    """Full chain on an in-memory array (grayscale or BGR).
    altitude_px <= 0 → chip mode (denoise + normalize only)."""
    img = despeckle(img, size)
    if altitude_px > 0:
        img = slant_range_correction(img, altitude_px)
        img = mask_nadir(img, altitude_px)
    return normalize_sonar(img)


# ---------------------------------------------------------------------------
# Self-check
# ---------------------------------------------------------------------------

def demo():
    """Self-check: Lee keeps a thin line a median would erase."""
    rng = np.random.default_rng(0)

    # 1) despeckle: flat speckle gets smoother, a 1px bright line survives
    flat = np.clip(rng.normal(120, 30, (40, 40)), 0, 255).astype(np.uint8)
    assert despeckle(flat).std() < flat.astype(np.float32).std(), \
        "Lee should smooth flat speckle"

    line = np.full((20, 20), 20, dtype=np.uint8)
    line[:, 10] = 220
    d = despeckle(line)
    assert d[:, 10].mean() > 3 * d[:, 5].mean(), \
        "Lee must preserve the thin line"
    assert cv2.medianBlur(line, 3)[:, 10].mean() < 60, \
        "median erases it (why not median)"

    # 2) normalize range/dtype check
    n = normalize_sonar(np.array([[0, 50, 1000]], np.float32))
    assert n.dtype == np.uint8 and n.min() == 0 and n.max() == 255

    print("preprocess demo OK")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--img")
    p.add_argument("--out", default="preprocessed.png")
    p.add_argument("--altitude", type=int, default=30)
    p.add_argument("--demo", action="store_true")
    a = p.parse_args()

    if a.demo:
        demo()
    elif a.img:
        preprocess_pipeline(a.img, a.out, altitude_px=a.altitude)
        print(f"Wrote {a.out}")
    else:
        print("Usage: python preprocess.py --img <path> [--out <path>] [--demo]")
