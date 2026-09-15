import cv2
import glob

def draw_boxes():
    imgs = glob.glob("Ultimate_Marine_Dataset/images/train/subpipe_*.jpg")[:2]
    for i, img_path in enumerate(imgs):
        img = cv2.imread(img_path)
        txt_path = img_path.replace('images', 'labels').replace('.jpg', '.txt')
        
        with open(txt_path, 'r') as f:
            lines = f.readlines()
            
        H, W, _ = img.shape
        for l in lines:
            p = l.strip().split()
            if not p: continue
            cx, cy, bw, bh = map(float, p[1:5])
            x1 = int((cx - bw/2) * W)
            y1 = int((cy - bh/2) * H)
            x2 = int((cx + bw/2) * W)
            y2 = int((cy + bh/2) * H)
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 255), 2)
            
        cv2.imwrite(f"/home/tharoon/.gemini/antigravity-cli/brain/0ee9051b-969a-46ce-84c1-f729dc57135b/scratch/real_pipe_{i}.jpg", img)

draw_boxes()
