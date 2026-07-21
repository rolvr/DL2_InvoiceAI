"""
ocr.py — OCR over detected region crops.

Owner: Damir. Deliberately runs OCR only on cropped regions (produced by Jordan's detector),
not on the full invoice image — this keeps the pipeline detection-first per the project's
Deep Learning II scope, and gives much better OCR accuracy than whole-page OCR.

Two backends are supported: EasyOCR (default — no external binary needed, generally more
robust on varied fonts) and PyTesseract (fallback / comparison — requires the Tesseract
binary installed on the system / Colab).
"""

from typing import Literal

import numpy as np


def crop_region(image: np.ndarray, box: tuple[float, float, float, float]) -> np.ndarray:
    """Crop (xmin, ymin, xmax, ymax) from an image, clamped to image bounds."""
    h, w = image.shape[:2]
    xmin, ymin, xmax, ymax = box
    xmin, ymin = max(0, int(xmin)), max(0, int(ymin))
    xmax, ymax = min(w, int(xmax)), min(h, int(ymax))
    return image[ymin:ymax, xmin:xmax]


def ocr_with_easyocr(image_crop: np.ndarray, reader=None, languages: list[str] | None = None) -> dict:
    """Run EasyOCR on a single cropped region. `reader` should be a cached
    easyocr.Reader(languages) instance — creating one per call is slow, so build it once
    in the notebook and pass it in.

    Returns {"text": str, "confidence": float} — confidence is the mean of per-line
    confidences returned by EasyOCR.
    """
    import easyocr  # local import: heavy dependency, only needed if this path is used

    if reader is None:
        reader = easyocr.Reader(languages or ["en"])

    results = reader.readtext(image_crop)
    if not results:
        return {"text": "", "confidence": 0.0}

    texts = [r[1] for r in results]
    confidences = [r[2] for r in results]
    return {"text": " ".join(texts), "confidence": float(np.mean(confidences))}


def ocr_with_tesseract(image_crop: np.ndarray) -> dict:
    """Run PyTesseract on a single cropped region.

    Returns {"text": str, "confidence": float} — confidence is the mean word-level
    confidence reported by Tesseract (ignoring -1 = no confidence entries).
    """
    import pytesseract  # local import: requires the tesseract binary on PATH

    data = pytesseract.image_to_data(image_crop, output_type=pytesseract.Output.DICT)
    words = [w for w in data["text"] if w.strip()]
    confs = [float(c) for c, w in zip(data["conf"], data["text"]) if w.strip() and float(c) >= 0]

    return {
        "text": " ".join(words),
        "confidence": float(np.mean(confs)) if confs else 0.0,
    }


def run_ocr(
    image_crop: np.ndarray,
    engine: Literal["easyocr", "tesseract"] = "easyocr",
    reader=None,
) -> dict:
    """Dispatch to the selected OCR engine. Default is EasyOCR."""
    if engine == "easyocr":
        return ocr_with_easyocr(image_crop, reader=reader)
    elif engine == "tesseract":
        return ocr_with_tesseract(image_crop)
    raise ValueError(f"Unknown OCR engine: {engine}")


def ocr_regions(
    image: np.ndarray,
    region_boxes: list[dict],
    engine: Literal["easyocr", "tesseract"] = "easyocr",
    reader=None,
) -> list[dict]:
    """Run OCR over a list of region boxes (as produced by Jordan's detector, each a dict
    with at least "label", "xmin", "ymin", "xmax", "ymax").

    Returns a list of dicts: {"label":, "text":, "confidence":}
    """
    results = []
    for box in region_boxes:
        crop = crop_region(image, (box["xmin"], box["ymin"], box["xmax"], box["ymax"]))
        if crop.size == 0:
            results.append({"label": box["label"], "text": "", "confidence": 0.0})
            continue
        ocr_result = run_ocr(crop, engine=engine, reader=reader)
        results.append({"label": box["label"], **ocr_result})
    return results
