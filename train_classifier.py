"""Prepare the existing YOLO detection dataset and train a YOLO image classifier.

The current dataset contains bounding-box labels, while classification training
expects one directory per class. This script crops every labelled object and
builds that directory structure before starting YOLO26 classification training.

Example:
    python train_classifier.py --prepare-only
    python train_classifier.py --epochs 50 --device 0
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from PIL import Image
from ultralytics import YOLO


ROOT = Path(__file__).resolve().parent
SOURCE_DATASET = ROOT / "campus-swap-dataset"
CLASSIFICATION_DATASET = ROOT / "campus-swap-classification"

CLASS_GROUPS = {
    "Books": {"Book"},
    "Electronics": {"E-waste_Misc", "Laptop", "Phone"},
    "Stationery": {"Pen"},
    "Furniture": {
        "Bed", "Cabinet", "Chair", "Closet", "Cupboard", "Dining Table",
        "Lamp", "Nightstand", "Shelf", "Sideboard", "Sofa", "TV stand", "Table",
    },
    "Other": {"Barcode"},
}


def read_names() -> list[str]:
    """Read class names from the existing data.yaml without adding a YAML dependency."""
    yaml_path = SOURCE_DATASET / "data.yaml"
    for line in yaml_path.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("names:"):
            value = line.split(":", 1)[1].strip()
            return [name.strip().strip("'\"") for name in value.strip("[]").split(",")]
    raise ValueError(f"Could not find names in {yaml_path}")


def target_class(label_name: str) -> str | None:
    for destination, source_names in CLASS_GROUPS.items():
        if label_name in source_names:
            return destination
    return None


def prepare_dataset() -> dict[str, int]:
    if CLASSIFICATION_DATASET.exists():
        shutil.rmtree(CLASSIFICATION_DATASET)

    names = read_names()
    counts = {class_name: 0 for class_name in CLASS_GROUPS}

    for split in ("train", "valid", "test"):
        source_images = SOURCE_DATASET / split / "images"
        source_labels = SOURCE_DATASET / split / "labels"
        destination_split = "val" if split == "valid" else split
        if not source_images.exists() or not source_labels.exists():
            continue

        for label_path in source_labels.glob("*.txt"):
            image_path = next(
                (source_images / f"{label_path.stem}{extension}"
                 for extension in (".jpg", ".jpeg", ".png", ".JPG", ".JPEG", ".PNG")
                 if (source_images / f"{label_path.stem}{extension}").exists()),
                None,
            )
            if image_path is None:
                continue

            with Image.open(image_path) as image:
                width, height = image.size
                for object_number, line in enumerate(label_path.read_text(encoding="utf-8").splitlines()):
                    fields = line.split()
                    if len(fields) != 5:
                        continue
                    class_id, x_center, y_center, box_width, box_height = map(float, fields)
                    if not 0 <= int(class_id) < len(names):
                        continue
                    class_name = target_class(names[int(class_id)])
                    if class_name is None:
                        continue

                    left = max(0, int((x_center - box_width / 2) * width))
                    top = max(0, int((y_center - box_height / 2) * height))
                    right = min(width, int((x_center + box_width / 2) * width))
                    bottom = min(height, int((y_center + box_height / 2) * height))
                    if right <= left or bottom <= top:
                        continue

                    output_dir = CLASSIFICATION_DATASET / destination_split / class_name
                    output_dir.mkdir(parents=True, exist_ok=True)
                    output_path = output_dir / f"{label_path.stem}_{object_number}.jpg"
                    image.crop((left, top, right, bottom)).convert("RGB").save(output_path, quality=95)
                    counts[class_name] += 1

    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--imgsz", type=int, default=224)
    parser.add_argument("--batch", type=int, default=32)
    parser.add_argument("--device", default="cpu", help="cpu, 0, or another CUDA device")
    args = parser.parse_args()

    counts = prepare_dataset()
    print("Prepared classification dataset:", counts)
    if args.prepare_only:
        return

    model = YOLO("yolo26n-cls.pt")
    model.train(
        data=str(CLASSIFICATION_DATASET),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        workers=0 if args.device == "cpu" else 4,
        patience=10,
        project=str(ROOT / "runs" / "classify"),
        name="campus_swap",
    )


if __name__ == "__main__":
    main()
