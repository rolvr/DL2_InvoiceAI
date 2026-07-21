"""
annotation_utils.py — read/write helpers for the shared bounding-box CSV schema:

    document_id,image_path,label,xmin,ymin,xmax,ymax,split,annotation_source

Used by Diana (stamp/signature boxes) and Jordan (region boxes), and by
scripts/convert_annotations.py when importing LabelImg/makesense.ai exports.
"""

from pathlib import Path

import pandas as pd

ANNOTATION_COLUMNS = [
    "document_id", "image_path", "label",
    "xmin", "ymin", "xmax", "ymax",
    "split", "annotation_source",
]


def load_annotations(csv_path: Path, labels: list[str] | None = None) -> pd.DataFrame:
    """Load a bbox annotation CSV, optionally filtered to a subset of labels
    (e.g. label_schema.json's region_labels or visual_element_labels)."""
    if not csv_path.exists():
        raise FileNotFoundError(f"Annotation file not found: {csv_path}")
    df = pd.read_csv(csv_path)
    missing_cols = set(ANNOTATION_COLUMNS) - set(df.columns)
    if missing_cols:
        raise ValueError(f"{csv_path} is missing expected columns: {missing_cols}")
    if labels:
        df = df[df["label"].isin(labels)]
    return df.reset_index(drop=True)


def boxes_for_image(df: pd.DataFrame, document_id: str) -> list[dict]:
    """Return all annotation boxes for one document_id as a list of dicts."""
    rows = df[df["document_id"] == document_id]
    return rows[["label", "xmin", "ymin", "xmax", "ymax"]].to_dict(orient="records")


def append_annotations(rows: list[dict], csv_path: Path) -> None:
    """Append new annotation rows to an existing (or new) CSV, keeping the shared schema."""
    new_df = pd.DataFrame(rows, columns=ANNOTATION_COLUMNS)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    if csv_path.exists():
        existing = pd.read_csv(csv_path)
        combined = pd.concat([existing, new_df], ignore_index=True)
    else:
        combined = new_df
    combined.to_csv(csv_path, index=False)
