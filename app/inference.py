"""
inference.py — framework-free inference layer for the FastAPI service.

Mirrors the Streamlit app's ``run_live()`` / ``run_live_ocr()`` (see app/streamlit_app.py) but
with NO Streamlit dependency, so it can be imported by app/api.py, the notebooks, or tests.

Design goals (identical to the demo, kept deliberately in sync):
  * Load the three real trained YOLO detectors (region / stamp / signature) from ``models/``
    and EasyOCR lazily, and cache them so the weights are read once per process.
  * DEGRADE GRACEFULLY / FAIL-CLOSED: if a model's weights are missing from ``models/`` — or the
    optional heavy libraries (ultralytics / easyocr / opencv) aren't installed — the corresponding
    signal is reported as "unavailable" rather than crashing. The verdict engine then treats those
    signals as ``unknown`` and fails-closed, which is the correct production behaviour for a
    readiness gate: never pass what you cannot confirm.

CPU-only, no GPU — matches the demo.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np

from src.config import PATHS


# ---------------------------------------------------------------------------
# Weights discovery + cached model loaders
# ---------------------------------------------------------------------------
def _weights(sub: str) -> Path | None:
    """Return models/<sub>/best.pt if it exists, else None."""
    p = PATHS.models_dir / sub / "best.pt"
    return p if p.exists() else None


@lru_cache(maxsize=4)
def _load_yolo(weights_path: str):
    from ultralytics import YOLO  # lazy: only needed when weights are present

    return YOLO(weights_path)


@lru_cache(maxsize=1)
def _load_easyocr_reader():
    import easyocr  # lazy: heavy import, CPU weights downloaded on first use

    return easyocr.Reader(["en"], gpu=False, verbose=False)


def detectors_available() -> dict:
    """Which detectors have weights on disk right now (used by /health)."""
    return {
        "region": _weights("region_detector") is not None,
        "stamp_signature": (_weights("stamp_detector") is not None
                            or _weights("signature_detector") is not None),
    }


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------
def run_detectors(image_bgr: np.ndarray, conf: float = 0.25) -> dict:
    """Run whatever detectors have weights present.

    Returns:
        {
          "stamp_sig_rows": [{"label", "confidence", "xmin","ymin","xmax","ymax"}, ...],
          "region_rows":    [{"region_label", "confidence", "xmin","ymin","xmax","ymax"}, ...],
          "vision_available": bool,   # stamp/signature model ran
          "region_available": bool,   # region model ran
          "notes": [str, ...],        # any degradation reasons (missing weights / libs)
        }
    """
    out = {"stamp_sig_rows": [], "region_rows": [],
           "vision_available": False, "region_available": False, "notes": []}

    ss = _weights("stamp_detector") or _weights("signature_detector")
    if ss:
        try:
            m = _load_yolo(str(ss))
            pr = m.predict(image_bgr, conf=conf, verbose=False)[0]
            names = pr.names
            for c, b, cf in zip(pr.boxes.cls.cpu().numpy(), pr.boxes.xyxy.cpu().numpy(),
                                pr.boxes.conf.cpu().numpy()):
                out["stamp_sig_rows"].append({
                    "label": names[int(c)], "confidence": round(float(cf), 3),
                    "xmin": float(b[0]), "ymin": float(b[1]),
                    "xmax": float(b[2]), "ymax": float(b[3])})
            out["vision_available"] = True
        except Exception as e:  # pragma: no cover - depends on optional heavy deps
            out["notes"].append(f"stamp/signature model failed to run: {e}")
    else:
        out["notes"].append("stamp/signature weights not found in models/ — visual signals unknown")

    rw = _weights("region_detector")
    if rw:
        try:
            m = _load_yolo(str(rw))
            pr = m.predict(image_bgr, conf=conf, verbose=False)[0]
            names = pr.names
            for c, b, cf in zip(pr.boxes.cls.cpu().numpy(), pr.boxes.xyxy.cpu().numpy(),
                                pr.boxes.conf.cpu().numpy()):
                out["region_rows"].append({
                    "region_label": names[int(c)], "confidence": round(float(cf), 3),
                    "xmin": float(b[0]), "ymin": float(b[1]),
                    "xmax": float(b[2]), "ymax": float(b[3])})
            out["region_available"] = True
        except Exception as e:  # pragma: no cover
            out["notes"].append(f"region model failed to run: {e}")
    else:
        out["notes"].append("region weights not found in models/ — region signals unknown")

    return out


# ---------------------------------------------------------------------------
# OCR
# ---------------------------------------------------------------------------
def run_ocr(image_bgr: np.ndarray, target_width: int = 700) -> str | None:
    """Run EasyOCR (CPU) over the downscaled full page, returning combined text or None.

    None => OCR engine unavailable/failed => caller treats reference/date/terms as unknown
    (fail-closed). Downscaling to ~700px keeps a full-page CPU pass to ~15-20s.
    """
    try:
        reader = _load_easyocr_reader()
    except Exception:
        return None
    try:
        small = image_bgr
        try:
            import cv2

            h, w = image_bgr.shape[:2]
            if w > target_width:
                scale = target_width / w
                small = cv2.resize(image_bgr, (int(w * scale), int(h * scale)))
        except Exception:
            pass  # opencv optional — OCR on full res still works, just slower
        results = reader.readtext(small, detail=0, paragraph=True)
        text = " ".join(results).strip()
        return text or None
    except Exception:
        return None
