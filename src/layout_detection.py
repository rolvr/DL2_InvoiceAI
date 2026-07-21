"""
layout_detection.py — invoice region ("layout") detection.

Owner: Jordan. Placeholder interface for SSD-style region detection over the 14 region
labels in config/label_schema.json. Fill in `load_region_detector` / `predict_regions`
with your trained model (SSD via TensorFlow Object Detection API / torchvision, or the
documented YOLOv8 fallback via ultralytics).

Keeping this as a thin wrapper means Damir and Hessam can call `predict_regions(image)`
without caring which framework/architecture is behind it.
"""

from pathlib import Path
from typing import Any

import numpy as np

from src.config import PATHS, load_label_schema

REGION_LABELS = load_label_schema()["region_labels"]


def load_region_detector(model_dir: Path | None = None) -> Any:
    """Load the trained region detector from models/region_detector/.

    TODO(Jordan): implement — return whatever object `predict_regions` expects
    (e.g. an ultralytics YOLO() instance, or a loaded torchvision/TF SavedModel).
    """
    model_dir = model_dir or (PATHS.models_dir / "region_detector")
    raise NotImplementedError(
        f"load_region_detector() is a placeholder. Implement in Jordan's notebook and here, "
        f"loading from {model_dir}."
    )


def predict_regions(image: np.ndarray, model: Any, confidence_threshold: float = 0.5) -> list[dict]:
    """Run the region detector on a single (preprocessed) image.

    Must return a list of dicts:
        {"label": <one of REGION_LABELS>, "xmin":, "ymin":, "xmax":, "ymax":, "confidence":}

    TODO(Jordan): implement using the loaded `model`.
    """
    raise NotImplementedError("predict_regions() is a placeholder — implement in Jordan's notebook.")
