"""
convert_annotations.py

Converts bounding-box annotation exports (Pascal VOC XML from LabelImg, or YOLO .txt) into
the shared project CSV schema used by data/annotations/*.csv:

    document_id,image_path,label,xmin,ymin,xmax,ymax,split,annotation_source

Usage:
    # Convert a folder of Pascal VOC XML files (LabelImg default export format)
    python scripts/convert_annotations.py --format voc \\
        --input_dir data/annotations/raw_voc \\
        --output_csv data/annotations/layout_bboxes.csv \\
        --split train --source labelimg

    # Convert a folder of YOLO-format .txt files (needs image dims to denormalize boxes)
    python scripts/convert_annotations.py --format yolo \\
        --input_dir data/annotations/raw_yolo \\
        --images_dir data/raw/invoices \\
        --classes_file data/annotations/classes.txt \\
        --output_csv data/annotations/layout_bboxes.csv \\
        --split train --source makesense.ai

Notes:
  - If output_csv already exists, new rows are appended (not overwritten), so multiple
    annotation batches / annotators can be merged over time.
  - document_id defaults to the image filename stem; adjust here if your manifest uses a
    different convention.
"""

import argparse
import csv
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

CSV_COLUMNS = [
    "document_id", "image_path", "label",
    "xmin", "ymin", "xmax", "ymax",
    "split", "annotation_source",
]


def parse_voc_file(xml_path: Path, split: str, source: str) -> list[dict]:
    """Parse one Pascal VOC XML annotation file into a list of row dicts."""
    tree = ET.parse(xml_path)
    root = tree.getroot()

    filename = root.findtext("filename") or xml_path.stem
    document_id = Path(filename).stem

    rows = []
    for obj in root.findall("object"):
        label = obj.findtext("name")
        bbox = obj.find("bndbox")
        if bbox is None or label is None:
            continue
        rows.append({
            "document_id": document_id,
            "image_path": filename,
            "label": label,
            "xmin": bbox.findtext("xmin"),
            "ymin": bbox.findtext("ymin"),
            "xmax": bbox.findtext("xmax"),
            "ymax": bbox.findtext("ymax"),
            "split": split,
            "annotation_source": source,
        })
    return rows


def parse_yolo_file(
    txt_path: Path, images_dir: Path, classes: list[str], split: str, source: str
) -> list[dict]:
    """Parse one YOLO-format .txt file (normalized cx,cy,w,h) into row dicts.

    Requires a matching image file (same stem) in images_dir to recover pixel dimensions,
    since YOLO format stores normalized coordinates.
    """
    from PIL import Image  # local import so the VOC-only path doesn't require Pillow

    document_id = txt_path.stem
    image_candidates = list(images_dir.glob(f"{document_id}.*"))
    if not image_candidates:
        print(f"[WARN] No image found for {txt_path.name} in {images_dir}; skipping.")
        return []
    image_path = image_candidates[0]

    with Image.open(image_path) as img:
        width, height = img.size

    rows = []
    for line in txt_path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) != 5:
            continue
        cls_idx, cx, cy, w, h = parts
        cls_idx = int(cls_idx)
        label = classes[cls_idx] if cls_idx < len(classes) else f"class_{cls_idx}"

        cx, cy, w, h = float(cx), float(cy), float(w), float(h)
        xmin = (cx - w / 2) * width
        xmax = (cx + w / 2) * width
        ymin = (cy - h / 2) * height
        ymax = (cy + h / 2) * height

        rows.append({
            "document_id": document_id,
            "image_path": image_path.name,
            "label": label,
            "xmin": round(xmin, 1),
            "ymin": round(ymin, 1),
            "xmax": round(xmax, 1),
            "ymax": round(ymax, 1),
            "split": split,
            "annotation_source": source,
        })
    return rows


def write_rows(rows: list[dict], output_csv: Path) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    file_exists = output_csv.exists()
    with open(output_csv, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert bbox annotations to project CSV schema.")
    parser.add_argument("--format", choices=["voc", "yolo"], required=True)
    parser.add_argument("--input_dir", required=True, type=Path)
    parser.add_argument("--output_csv", required=True, type=Path)
    parser.add_argument("--split", default="train", choices=["train", "val", "test"])
    parser.add_argument("--source", default="manual", help="e.g. labelimg, makesense.ai, cvat")
    parser.add_argument("--images_dir", type=Path, help="Required for --format yolo")
    parser.add_argument("--classes_file", type=Path, help="Required for --format yolo (one class name per line)")
    args = parser.parse_args()

    if not args.input_dir.exists():
        print(f"[ERROR] input_dir does not exist: {args.input_dir}")
        return 1

    all_rows: list[dict] = []

    if args.format == "voc":
        xml_files = sorted(args.input_dir.glob("*.xml"))
        if not xml_files:
            print(f"[WARN] No .xml files found in {args.input_dir}")
        for xml_path in xml_files:
            all_rows.extend(parse_voc_file(xml_path, args.split, args.source))

    else:  # yolo
        if not args.images_dir or not args.classes_file:
            print("[ERROR] --format yolo requires --images_dir and --classes_file")
            return 1
        classes = [c.strip() for c in args.classes_file.read_text().splitlines() if c.strip()]
        txt_files = sorted(args.input_dir.glob("*.txt"))
        if not txt_files:
            print(f"[WARN] No .txt files found in {args.input_dir}")
        for txt_path in txt_files:
            all_rows.extend(parse_yolo_file(txt_path, args.images_dir, classes, args.split, args.source))

    if not all_rows:
        print("[WARN] No annotation rows produced — nothing written.")
        return 0

    write_rows(all_rows, args.output_csv)
    print(f"[OK] Wrote {len(all_rows)} rows to {args.output_csv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
