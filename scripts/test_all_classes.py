import glob, cv2, os
from ultralytics import YOLO

os.makedirs("/home/tharoon/.gemini/antigravity-cli/brain/0ee9051b-969a-46ce-84c1-f729dc57135b/scratch/test_preds", exist_ok=True)
model = YOLO("models/GhostNetSonar/best.pt")

def get_aircraft():
    for f in glob.glob("Ultimate_Marine_Dataset/labels/train/sctd_*.txt"):
        if "1 " in open(f).read():
            return f.replace("labels", "images").replace(".txt", ".jpg")
    return None

samples = {
  "Shipwreck": glob.glob("Ultimate_Marine_Dataset/images/train/shipwreck_*.jpg") + glob.glob("Ultimate_Marine_Dataset/images/train/sctd_*.jpg"),
  "Aircraft": [get_aircraft()],
  "Pipe": glob.glob("Ultimate_Marine_Dataset/images/train/pure_synth_subpipe_*.jpg"),
  "Cylinder": glob.glob("Ultimate_Marine_Dataset/images/train/pure_synth_uatd_*.jpg"),
  "Ghost_Net": glob.glob("Ultimate_Marine_Dataset/images/train/synth_synth_net_*.jpg")
}

for name, imgs in samples.items():
    if imgs and imgs[0]:
        img_path = imgs[0]
        results = model.predict(img_path, conf=0.15)
        res_img = results[0].plot(labels=True, conf=True)
        out_name = f"/home/tharoon/.gemini/antigravity-cli/brain/0ee9051b-969a-46ce-84c1-f729dc57135b/scratch/test_preds/{name}.jpg"
        cv2.imwrite(out_name, res_img)
        print(f"Saved {name}")
