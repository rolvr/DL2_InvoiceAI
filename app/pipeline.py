"""
pipeline.py — the framework-free core the FastAPI service wraps.

This holds the actual "run the pipeline on one invoice image and assemble the readiness JSON"
logic, with NO FastAPI/HTTP dependency. app/api.py's POST /predict is a thin wrapper around
``predict_from_bytes`` here, which means the exact same code path is exercised by:
  * the FastAPI endpoint,
  * the pytest suite (no server needed),
  * any script/notebook that wants a programmatic prediction.

Steps: decode -> region + stamp/signature detection -> (optional) OCR -> derive signals ->
completeness score -> evaluate every preset policy. Every stage fails-closed when its model /
OCR engine is unavailable.
"""

from __future__ import annotations

import io
import time
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from app import inference
from src.completeness import score as completeness_score
from src.config import load_required_fields
from src.streamlit_helpers import signals_from_record
from src.verdict_engine import evaluate, preset_policies


class ImageDecodeError(ValueError):
    """Raised when uploaded bytes cannot be decoded as an image (maps to HTTP 400)."""


def decode_image(raw: bytes) -> np.ndarray:
    """Decode raw bytes into a BGR ndarray (matches the Streamlit app convention: RGB[:, :, ::-1])."""
    try:
        pil = Image.open(io.BytesIO(raw)).convert("RGB")
    except Exception as e:
        raise ImageDecodeError(str(e)) from e
    return np.array(pil)[:, :, ::-1]


def service_metadata() -> dict:
    return {
        "models": inference.detectors_available(),
        "required_fields": [f["field_name"] for f in load_required_fields()["default_required_fields"]],
        "presets": [p.to_dict() for p in preset_policies().values()],
    }


def predict_from_image(image_bgr: np.ndarray, *, filename: str = "uploaded_image",
                       confidence: float = 0.25, run_ocr: bool = True,
                       document_id: str | None = None) -> dict[str, Any]:
    """Run the full pipeline on an already-decoded BGR image and return the readiness JSON."""
    t0 = time.time()
    h, w = image_bgr.shape[:2]
    doc_id = document_id or Path(filename).stem

    # 1) Detectors (region + stamp/signature) — empty + unavailable when weights absent.
    det = inference.run_detectors(image_bgr, conf=confidence)

    # 2) OCR (optional) — None disables reference/date/terms signals (fail-closed).
    ocr_text = inference.run_ocr(image_bgr) if run_ocr else None

    # 3) Signals — assembled exactly like the Streamlit Live Demo / Showcase.
    record = {
        "document_id": doc_id,
        "visual_elements": {
            "stamp_detected": (any(r["label"] == "stamp" for r in det["stamp_sig_rows"])
                               if det["vision_available"] else None),
            "signature_detected": (any(r["label"] == "signature" for r in det["stamp_sig_rows"])
                                   if det["vision_available"] else None),
        },
        "payment_context": {},
    }
    signals = signals_from_record(record, ocr_text=ocr_text)

    # 4) Graded completeness score.
    region_labels = {r.get("region_label") for r in det["region_rows"]}
    completeness = completeness_score(signals, region_labels, ocr_text or "", None)

    # 5) Verdict under every preset policy.
    verdicts = {name: evaluate(signals, pol).as_dict() for name, pol in preset_policies().items()}

    degraded = not (det["region_available"] and det["vision_available"] and bool(ocr_text))

    return {
        "document_id": doc_id,
        "filename": filename,
        "image": {"width": int(w), "height": int(h)},
        "detections": {
            "regions": det["region_rows"],
            "visual_marks": det["stamp_sig_rows"],
            "region_model_available": det["region_available"],
            "stamp_signature_model_available": det["vision_available"],
            "notes": det["notes"],
        },
        "ocr": {"ran": bool(run_ocr), "text": ocr_text, "char_count": len(ocr_text) if ocr_text else 0},
        "signals": signals,
        "completeness": completeness,
        "verdicts": verdicts,
        "meta": {
            "confidence_threshold": confidence,
            "ocr_ran": bool(run_ocr),
            "device": "cpu",
            "degraded": degraded,
            "processing_time_ms": round((time.time() - t0) * 1000, 1),
        },
    }


def predict_from_bytes(raw: bytes, *, filename: str = "uploaded_image",
                       confidence: float = 0.25, run_ocr: bool = True,
                       document_id: str | None = None) -> dict[str, Any]:
    """Decode `raw` image bytes and run the pipeline. Raises ImageDecodeError on bad input."""
    if not raw:
        raise ImageDecodeError("empty upload")
    image_bgr = decode_image(raw)
    return predict_from_image(image_bgr, filename=filename, confidence=confidence,
                              run_ocr=run_ocr, document_id=document_id)
