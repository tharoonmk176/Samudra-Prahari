import json
import csv
import os

class GeoReferencer:
    def __init__(self, metadata_available=False, resolution_m_per_pixel=0.1, base_lat=None, base_lon=None, towfish_speed=3.0):
        self.metadata_available = metadata_available
        self.resolution = resolution_m_per_pixel
        self.base_lat = base_lat
        self.base_lon = base_lon
        self.towfish_speed = towfish_speed
        
        if not self.metadata_available and base_lat is None:
            print("WARNING: No GPS/XTF metadata available and no base coordinates provided.")
            print("         Skipping real Lat/Long coordinate generation.")
            
    def pixel_to_meters(self, pixel_x, pixel_y, image_width):
        """
        Converts pixel coordinates to relative meters from the sonar towfish.
        Assuming the towfish is at the center of the image (w // 2).
        """
        center_x = image_width / 2.0
        
        # Across-track distance (horizontal distance from the sensor)
        across_track_m = (pixel_x - center_x) * self.resolution
        
        # Along-track distance (vertical distance along the swath)
        along_track_m = pixel_y * self.resolution
        
        return round(across_track_m, 2), round(along_track_m, 2)
        
    def generate_report(self, detections, image_width, image_height, output_name="report"):
        """
        Generates Phase 5 structured JSON and CSV reports.
        """
        report_data = []
        
        for i, det in enumerate(detections):
            x1, y1, x2, y2 = det["box"]
            
            # Center of the bounding box
            center_x = (x1 + x2) / 2.0
            center_y = (y1 + y2) / 2.0
            
            # Dimensions in pixels
            width_px = x2 - x1
            height_px = y2 - y1
            
            # Relative physical location and dimensions
            across_m, along_m = self.pixel_to_meters(center_x, center_y, image_width)
            phys_width_m = round(width_px * self.resolution, 2)
            phys_height_m = round(height_px * self.resolution, 2)
            
            calc_lat = "N/A"
            calc_lon = "N/A"
            if self.base_lat is not None and self.base_lon is not None:
                calc_lat = round(self.base_lat + (along_m * 0.000009), 6)
                calc_lon = round(self.base_lon + (across_m * 0.000009), 6)
            
            record = {
                "id": i + 1,
                "lat": calc_lat,
                "long": calc_lon,
                "bounding_dimensions_m": f"{phys_width_m}x{phys_height_m}",
                "class": det["class"],
                "confidence": round(det["calibrated_conf"], 4),
                "across_track_m": across_m,
                "along_track_m": along_m
            }
            report_data.append(record)
            
        # Write JSON
        os.makedirs("outputs", exist_ok=True)
        json_path = f"outputs/{output_name}.json"
        with open(json_path, 'w') as f:
            json.dump(report_data, f, indent=4)
            
        # Write CSV
        csv_path = f"outputs/{output_name}.csv"
        if report_data:
            keys = ["id", "lat", "long", "bounding_dimensions_m", "class", "confidence", "across_track_m", "along_track_m"]
            with open(csv_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                for d in report_data:
                    writer.writerow(d)
                    
        print(f"\nPhase 4 & 5 Complete! Reports saved to {json_path} and {csv_path}")
        return report_data

if __name__ == "__main__":
    # Simulated detections from Phase 3 for testing
    mock_detections = [
        {"class": "aircraft", "box": (233, 179, 339, 347), "raw_conf": 0.92, "calibrated_conf": 0.98}
    ]
    
    geo = GeoReferencer(metadata_available=False, resolution_m_per_pixel=0.1)
    # Image 000002.jpg is 415x385
    geo.generate_report(mock_detections, image_width=415, image_height=385, output_name="detection_report")
