"""Geo-Referencing + Report Generator — UPGRADED with pyproj geodesics.

Converts detection pixel coordinates to real-world lat/lon using proper
WGS84 ellipsoidal geodesic math (via pyproj).  Computes physical bounding
dimensions in metres from the sonar's resolution scale.

KEY UPGRADES over the original:
  1. pyproj.Geod forward solve instead of crude `pixels * 0.000009`
  2. Proper across-track and along-track distance calculations
  3. Full detection provenance in reports (yolo_conf, shadow_score, etc.)
  4. CRS metadata in JSON output (EPSG:4326)
  5. Honest null coordinates when no GPS metadata is available

The GeoReferencer class interface is preserved for backward compatibility.
"""
import json
import csv
import os
import io
import math

try:
    from pyproj import Geod
    _GEOD = Geod(ellps="WGS84")
    _HAS_PYPROJ = True
except ImportError:
    _HAS_PYPROJ = False
    _GEOD = None


class GeoReferencer:
    """Converts pixel detections to geo-anchored intelligence reports.

    Parameters
    ----------
    metadata_available : bool
        True if real XTF/GPS metadata is available.
    resolution_m_per_pixel : float
        Across-track resolution in metres/pixel (from slant_range / samples).
    base_lat, base_lon : float or None
        Starting towfish coordinates.  None → coordinates are omitted (honest).
    heading : float
        Towfish heading in degrees (0 = north, 90 = east).
    towfish_speed : float
        Speed in knots (used to compute along-track resolution if no nav data).
    ping_rate : float
        Pings per second (used with speed to derive along-track m/px).
    """

    def __init__(self, metadata_available=False, resolution_m_per_pixel=0.1,
                 base_lat=None, base_lon=None, heading=0.0,
                 towfish_speed=3.0, ping_rate=10.0):
        self.metadata_available = metadata_available
        self.across_m_per_px = resolution_m_per_pixel
        self.base_lat = base_lat
        self.base_lon = base_lon
        self.heading = heading
        self.towfish_speed = towfish_speed
        self.ping_rate = ping_rate

        # Along-track resolution: speed_m/s / ping_rate
        speed_m_per_s = towfish_speed * 0.5144  # knots → m/s
        self.along_m_per_px = speed_m_per_s / max(ping_rate, 0.1)

        if base_lat is None and not metadata_available:
            print("WARNING: No GPS/XTF metadata and no base coordinates provided.")
            print("         Lat/Long will be null (never fabricated).")

    def pixel_to_meters(self, pixel_x, pixel_y, image_width):
        """Convert pixel coordinates to relative metres from the towfish.

        Assumes the towfish (nadir) is at the horizontal centre of the image.
        """
        center_x = image_width / 2.0
        across_track_m = (pixel_x - center_x) * self.across_m_per_px
        along_track_m = pixel_y * self.along_m_per_px
        return round(across_track_m, 2), round(along_track_m, 2)

    def _offset_to_latlon(self, along_m, across_m):
        """Convert along/across-track metres to lat/lon using geodesic math."""
        if self.base_lat is None or self.base_lon is None:
            return None, None

        if _HAS_PYPROJ:
            # Step 1: move along-track (forward along heading)
            lon1, lat1, _ = _GEOD.fwd(
                self.base_lon, self.base_lat, self.heading, along_m
            )
            # Step 2: move across-track (perpendicular to heading)
            perp_az = self.heading + (90.0 if across_m >= 0 else -90.0)
            lon2, lat2, _ = _GEOD.fwd(lon1, lat1, perp_az, abs(across_m))
            return round(lat2, 6), round(lon2, 6)
        else:
            # Fallback: simple approximation (less accurate but functional)
            lat = self.base_lat + (along_m * 0.000009)
            lon = self.base_lon + (across_m * 0.000009)
            return round(lat, 6), round(lon, 6)

    def generate_report(self, detections, image_width, image_height,
                        output_name="report"):
        """Generate structured JSON and CSV intelligence reports.

        Parameters
        ----------
        detections : list of dict
            Each must have: 'class', 'box' [x1,y1,x2,y2], 'calibrated_conf'.
            Optional: 'raw_conf', 'shadow_score', 'class_id'.
        image_width, image_height : int
            Dimensions of the image/mosaic the detections came from.
        output_name : str
            Output filename stem (without extension).

        Returns
        -------
        list of dict : The report records.
        """
        report_data = []

        for i, det in enumerate(detections):
            box = det["box"]
            x1, y1, x2, y2 = box[0], box[1], box[2], box[3]

            # Centre of bounding box
            cx = (x1 + x2) / 2.0
            cy = (y1 + y2) / 2.0

            # Pixel dimensions
            width_px = round(x2 - x1, 1)
            height_px = round(y2 - y1, 1)

            # Physical dimensions in metres
            width_m = round(width_px * self.across_m_per_px, 2)
            height_m = round(height_px * self.along_m_per_px, 2)

            # Relative position
            across_m, along_m = self.pixel_to_meters(cx, cy, image_width)

            # Geo-coordinates
            calc_lat, calc_lon = self._offset_to_latlon(along_m, across_m)

            # Confidence provenance
            conf = det.get("calibrated_conf", det.get("confidence", 0.0))
            raw_conf = det.get("raw_conf", conf)
            shadow_sc = det.get("shadow_score", None)

            record = {
                "id": i + 1,
                "class": det["class"],
                "confidence": round(conf, 4),
                "confidence_pct": round(conf * 100, 1),
                "yolo_conf": round(raw_conf, 4) if raw_conf else None,
                "shadow_score": round(shadow_sc, 3) if shadow_sc is not None else None,
                "lat": calc_lat,
                "lon": calc_lon,
                "across_track_m": across_m,
                "along_track_m": along_m,
                "width_px": width_px,
                "height_px": height_px,
                "width_m": width_m,
                "height_m": height_m,
                "bounding_dimensions_m": f"{width_m}x{height_m}",
            }
            report_data.append(record)

        # Write outputs
        os.makedirs("outputs", exist_ok=True)

        # JSON with CRS metadata
        json_path = f"outputs/{output_name}.json"
        with open(json_path, "w") as f:
            json.dump({
                "crs": "EPSG:4326",
                "count": len(report_data),
                "resolution_m_per_px": {
                    "across_track": self.across_m_per_px,
                    "along_track": round(self.along_m_per_px, 4)
                },
                "detections": report_data
            }, f, indent=4)

        # CSV
        csv_path = f"outputs/{output_name}.csv"
        if report_data:
            keys = list(report_data[0].keys())
            with open(csv_path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                writer.writerows(report_data)

        print(f"Reports saved: {json_path} and {csv_path}  ({len(report_data)} detections)")
        return report_data


# ---------------------------------------------------------------------------
# Utility: build records without writing files (for streaming/dashboard)
# ---------------------------------------------------------------------------

def build_records(detections, m_per_px=None):
    """Build report records in-memory (no file I/O).

    Parameters
    ----------
    detections : list of dict
    m_per_px : tuple (across, along) or None
    """
    recs = []
    for i, d in enumerate(detections):
        box = d["box"]
        x1, y1, x2, y2 = box[0], box[1], box[2], box[3]
        wpx = round(x2 - x1, 1)
        hpx = round(y2 - y1, 1)
        conf = float(d.get("calibrated_conf", d.get("conf", d.get("confidence", 0.0))))

        rec = {
            "id": i + 1,
            "class": d.get("class"),
            "confidence": round(conf, 3),
            "confidence_pct": round(conf * 100, 1),
            "yolo_conf": round(float(d["raw_conf"]), 3) if "raw_conf" in d else None,
            "shadow_score": round(float(d["shadow_score"]), 3) if "shadow_score" in d else None,
            "width_px": wpx,
            "height_px": hpx,
            "width_m": round(wpx * m_per_px[0], 2) if m_per_px else None,
            "height_m": round(hpx * m_per_px[1], 2) if m_per_px else None,
            "lat": d.get("lat"),
            "lon": d.get("lon"),
        }
        recs.append(rec)
    return recs


def to_json(recs):
    """Serialize records to JSON string with CRS metadata."""
    return json.dumps({
        "crs": "EPSG:4326",
        "count": len(recs),
        "detections": recs
    }, indent=2)


def to_csv(recs):
    """Serialize records to CSV string."""
    fields = list(recs[0].keys()) if recs else [
        "id", "class", "confidence", "lat", "lon"
    ]
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields)
    w.writeheader()
    w.writerows(recs)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Self-check
# ---------------------------------------------------------------------------

def demo():
    """Self-check: dimensions, coordinates, and report round-trip."""
    geo = GeoReferencer(
        metadata_available=False,
        resolution_m_per_pixel=0.2,
        base_lat=13.10,
        base_lon=80.30,
        heading=0.0,
        towfish_speed=3.0,
        ping_rate=10.0
    )

    dets = [
        {"class": "ship", "box": [100, 200, 200, 350],
         "calibrated_conf": 0.83, "raw_conf": 0.9, "shadow_score": 0.72},
        {"class": "aircraft", "box": [50, 50, 100, 100],
         "calibrated_conf": 0.45, "raw_conf": 0.55}
    ]

    recs = geo.generate_report(dets, image_width=500, image_height=400,
                               output_name="_test_report")

    # Check dimensions
    assert recs[0]["width_m"] == 20.0   # (200-100) * 0.2
    assert recs[0]["height_m"] is not None
    assert recs[0]["lat"] is not None   # we provided base coords

    # Check provenance
    assert recs[0]["yolo_conf"] == 0.9
    assert recs[0]["shadow_score"] == 0.72
    assert recs[1]["shadow_score"] is None  # not provided

    # Clean up test files
    for ext in (".json", ".csv"):
        p = f"outputs/_test_report{ext}"
        if os.path.exists(p):
            os.remove(p)

    print("geo_report demo OK")


if __name__ == "__main__":
    demo()
