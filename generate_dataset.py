"""
generate_dataset.py

Batch-generates a synthetic side-scan sonar training set: for each sample,
randomly pick a seabed type, optionally place an object (ghost net / cylinder
/ wreck), render it with sonar_shadow_render, and save:
  - <id>.png            grayscale sonar chip
  - <id>_mask.png       binary object mask (for U-Net style segmentation)
  - metadata.csv        one row per chip: class, bbox, altitude, seabed type
                         (for YOLO/Faster R-CNN style detection + your
                         confidence-scoring / geotagging report format)

Run: python3 generate_dataset.py --n 40 --out /mnt/user-data/outputs/dataset_samples
"""

import argparse
import csv
import os

import numpy as np
from PIL import Image

from net_mesh_generator import (
    generate_seabed_baseline, generate_tangled_net, generate_cylinder, generate_wreck_hull
)
from sonar_shadow_render import render_sonar_chip, to_uint8


ALONG, ACROSS = 256, 384   # pixels per chip
DX = 0.04                  # meters per across-track pixel


def make_sample(idx, rng, out_dir):
    seabed_type = rng.choice(["flat_mud", "sandy_ripples", "rocky"], p=[0.35, 0.4, 0.25])
    seabed_seed = int(rng.integers(0, 1_000_000))
    seabed = generate_seabed_baseline(ALONG, ACROSS, seabed_type=seabed_type, seed=seabed_seed)

    has_object = rng.random() < 0.7
    obj_class = "background"
    obj_height = np.zeros_like(seabed)

    if has_object:
        obj_class = rng.choice(["ghost_net", "cylinder", "wreck"], p=[0.5, 0.25, 0.25])
        obj_seed = int(rng.integers(0, 1_000_000))
        if obj_class == "ghost_net":
            obj_height = generate_tangled_net(
                ALONG, ACROSS,
                extent_along=rng.uniform(40, 90), extent_across=rng.uniform(40, 90),
                mean_height=rng.uniform(0.08, 0.25),
                tangle_density=rng.uniform(0.4, 0.85),
                seed=obj_seed,
            )
            obj_reflectivity = rng.uniform(0.5, 0.75)  # nets: patchy, weaker return than metal
        elif obj_class == "cylinder":
            obj_height = generate_cylinder(
                ALONG, ACROSS,
                length=rng.uniform(30, 70), radius=rng.uniform(6, 16), seed=obj_seed,
            )
            obj_reflectivity = rng.uniform(0.85, 1.1)
        else:  # wreck
            obj_height = generate_wreck_hull(
                ALONG, ACROSS,
                length=rng.uniform(90, 180), beam=rng.uniform(25, 45),
                hull_height=rng.uniform(0.8, 2.0), seed=obj_seed,
            )
            obj_reflectivity = rng.uniform(0.9, 1.2)

    altitude = rng.uniform(6.0, 14.0)
    render_seed = int(rng.integers(0, 1_000_000))
    image, obj_mask, shadow_mask = render_sonar_chip(
        seabed, obj_height, altitude=altitude, dx=DX,
        base_seabed_reflectivity=rng.uniform(0.25, 0.45),
        object_reflectivity=obj_reflectivity if has_object else 0.35,
        look_number=rng.integers(2, 5),
        seed=render_seed,
    )

    img_u8 = to_uint8(image)
    mask_u8 = (obj_mask * 255).astype(np.uint8)

    fname = f"chip_{idx:04d}"
    Image.fromarray(img_u8, mode="L").save(os.path.join(out_dir, f"{fname}.png"))
    Image.fromarray(mask_u8, mode="L").save(os.path.join(out_dir, f"{fname}_mask.png"))

    bbox = bbox_from_mask(obj_mask)
    return {
        "filename": f"{fname}.png",
        "class": obj_class,
        "seabed_type": seabed_type,
        "altitude_m": round(float(altitude), 2),
        "bbox_x_min": bbox[0], "bbox_y_min": bbox[1],
        "bbox_x_max": bbox[2], "bbox_y_max": bbox[3],
    }


def bbox_from_mask(mask):
    ys, xs = np.where(mask)
    if len(xs) == 0:
        return ("", "", "", "")
    return (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--out", type=str, default="/mnt/user-data/outputs/dataset_samples")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    rng = np.random.default_rng(args.seed)

    rows = []
    for i in range(args.n):
        rows.append(make_sample(i, rng, args.out))
        if (i + 1) % 10 == 0:
            print(f"generated {i + 1}/{args.n}")

    with open(os.path.join(args.out, "metadata.csv"), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"Done. {args.n} chips written to {args.out}")


if __name__ == "__main__":
    main()
