"""
results_store.py — read the pipeline outputs the members publish, tolerating "not there yet".

Owner: Hessam (integration). The demo app's Gallery/Batch/Report views read pre-computed results
from `outputs/`; this module loads them defensively so the app runs end-to-end even while the
three member notebooks are still executing on Colab and their outputs have not been copied in.

Everything returns an empty / clearly-flagged structure rather than raising, so the UI can show
"waiting for <member>'s output" instead of crashing.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from src.config import PATHS


# ---------------------------------------------------------------------------
# low-level readers
# ---------------------------------------------------------------------------
def _read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        import pandas as pd
        return pd.read_csv(path).to_dict("records")
    except Exception:
        return []


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# per-member availability + data
# ---------------------------------------------------------------------------
def _pred(name: str) -> Path:
    return PATHS.predictions_dir / name


def _metric(name: str) -> Path:
    return PATHS.metrics_dir / name


def availability() -> dict[str, bool]:
    """Which member outputs are present on disk right now (drives the 'waiting for X' UI)."""
    return {
        "rolando_manifest": (PATHS.processed_dir / "invoice_manifest.csv").exists(),
        "diana_predictions": _pred("stamp_signature_predictions.csv").exists(),
        "jordan_predictions": _pred("region_predictions.csv").exists(),
        "damir_ocr": _pred("ocr_outputs.csv").exists(),
        "diana_metrics": _metric("stamp_signature_metrics.json").exists(),
        "jordan_metrics": _metric("region_iou_metrics.json").exists(),
        "damir_metrics": _metric("ocr_parameter_metrics.json").exists(),
        "final_json": PATHS.final_json_dir.exists() and any(PATHS.final_json_dir.glob("*.json")),
    }


def load_manifest() -> list[dict]:
    return _read_csv(PATHS.processed_dir / "invoice_manifest.csv")


def load_stamp_signature() -> list[dict]:
    return _read_csv(_pred("stamp_signature_predictions.csv"))


def load_regions() -> list[dict]:
    return _read_csv(_pred("region_predictions.csv"))


def load_ocr_outputs() -> list[dict]:
    return _read_csv(_pred("ocr_outputs.csv"))


def load_metrics() -> dict[str, dict]:
    """All members' metric JSONs, keyed by short name (missing ones omitted)."""
    out = {}
    for key, fname in [("stamp_signature", "stamp_signature_metrics.json"),
                       ("region_iou", "region_iou_metrics.json"),
                       ("ocr_parameter", "ocr_parameter_metrics.json")]:
        d = _read_json(_metric(fname))
        if d:
            out[key] = d
    return out


def load_final_records() -> list[dict]:
    """Every per-invoice final JSON Hessam's integration wrote (empty until nb05 runs)."""
    if not PATHS.final_json_dir.exists():
        return []
    records = []
    for p in sorted(PATHS.final_json_dir.glob("*.json")):
        d = _read_json(p)
        if d:
            records.append(d)
    return records


# ---------------------------------------------------------------------------
# invoice-keyed OCR text (for reference/date/terms derivation)
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def invoice_ocr_text() -> dict[str, str]:
    """document_id -> OCR text for the invoices we actually have text for.

    Sources, in priority order:
      1. Damir's ocr_outputs.csv rows with source == 'invoice_batch1' (real OCR of invoices)
      2. the batch_1 annotation CSVs' 'OCRed Text' column (ground-truth OCR for ~197 invoices)
    Damir's other rows are receipt-dataset text and are intentionally ignored here.
    """
    text: dict[str, str] = {}

    for row in load_ocr_outputs():
        if str(row.get("source", "")).startswith("invoice"):
            doc = str(row.get("document_id", "")).strip()
            t = row.get("ocr_text")
            if doc and isinstance(t, str) and t.strip():
                text.setdefault(doc, t)

    ann_dir = PATHS.data_dir / "annotations"
    for csv_path in sorted((PATHS.raw_dir / "invoices").rglob("batch1_*.csv")) or \
            sorted(ann_dir.glob("batch1_*.csv")):
        for row in _read_csv(csv_path):
            stem = str(row.get("File Name", "")).replace(".jpg", "").strip()
            t = row.get("OCRed Text")
            if stem and isinstance(t, str) and t.strip():
                text.setdefault(stem, t)

    return text


def build_record_index() -> dict[str, dict]:
    """document_id -> final JSON record (for the gallery drilldown)."""
    return {r.get("document_id"): r for r in load_final_records() if r.get("document_id")}
