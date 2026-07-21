"""
stamp_signature_detection.py — stamp and signature detection.

Owner: Diana. Placeholder interface — stamp and signature are always kept as two
distinct labels ("stamp", "signature"); never merge them into one class.

Fill in `load_stamp_detector` / `load_signature_detector` / `predict_stamp_signature`
with your trained model(s) (one shared multi-class detector, or two separate detectors —
either is fine as long as the output uses these exact label strings).
"""

from pathlib import Path
from typing import Any

import numpy as np

from src.config import PATHS

STAMP_LABEL = "stamp"
SIGNATURE_LABEL = "signature"
VISUAL_ELEMENT_LABELS = [STAMP_LABEL, SIGNATURE_LABEL]


def load_stamp_detector(model_dir: Path | None = None) -> Any:
    """TODO(Diana): load trained stamp detector from models/stamp_detector/."""
    model_dir = model_dir or (PATHS.models_dir / "stamp_detector")
    raise NotImplementedError(f"load_stamp_detector() is a placeholder. Load from {model_dir}.")


def load_signature_detector(model_dir: Path | None = None) -> Any:
    """TODO(Diana): load trained signature detector from models/signature_detector/."""
    model_dir = model_dir or (PATHS.models_dir / "signature_detector")
    raise NotImplementedError(f"load_signature_detector() is a placeholder. Load from {model_dir}.")


def predict_stamp_signature(
    image: np.ndarray,
    stamp_model: Any,
    signature_model: Any,
    confidence_threshold: float = 0.5,
) -> list[dict]:
    """Run both detectors on a single (preprocessed) image.

    Must return a list of dicts, each with "label" being exactly "stamp" or "signature":
        {"label": "stamp"|"signature", "xmin":, "ymin":, "xmax":, "ymax":, "confidence":}

    TODO(Diana): implement using the loaded models.
    """
    raise NotImplementedError("predict_stamp_signature() is a placeholder — implement in Diana's notebook.")
