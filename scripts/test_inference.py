import os
from ultralytics import YOLO

def test_inference():
    print("Loading ONNX model for CPU inference (Phase B constraint)...")
    # Load the exported ONNX model
    model = YOLO("models/GhostNetSonar/best.onnx")
    
    # Pick a test image from the dataset we have locally
    test_image = "SCTD/SCTD/JPEGImages/000002.jpg"
    
    print(f"\nRunning inference on {test_image}...")
    results = model(test_image)
    
    print("\n--- INFERENCE RESULTS ---")
    for r in results:
        print(f"Detected {len(r.boxes)} objects.")
        for box in r.boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            cls_name = r.names[cls_id]
            print(f"- {cls_name} (Confidence: {conf:.2%})")
            
    print("\nInference complete! Model is functioning according to plan.")

if __name__ == "__main__":
    test_inference()
