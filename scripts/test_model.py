from ultralytics import YOLO
import cv2
import glob
import random

# Load the trained model
model = YOLO("trained_model/GhostNetSonar_Weights/best.pt")

# Pick test images
test_images = []
# 1. A shipwreck/aircraft from SCTD
sctd_imgs = glob.glob("SCTD/SCTD/JPEGImages/*.jpg")
if sctd_imgs: test_images.append(random.choice(sctd_imgs))
# 2. A pipe/cylinder from 20xx
pipe_imgs = glob.glob("dataset/Nexus/2010/2010/*.jpg")
if pipe_imgs: test_images.append(random.choice(pipe_imgs))
# 3. A synthetic ghost net
net_imgs = glob.glob("synthetic_nets/images/*.jpg")
if net_imgs: test_images.append(random.choice(net_imgs))

for img_path in test_images:
    print(f"\n--- Testing on {img_path} ---")
    results = model.predict(img_path, conf=0.25)
    for r in results:
        boxes = r.boxes
        for box in boxes:
            cls = int(box.cls[0])
            conf = float(box.conf[0])
            class_name = model.names[cls]
            print(f"Detected: {class_name} with confidence {conf:.2f}")
