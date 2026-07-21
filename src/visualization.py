"""
visualization.py — shared plotting helpers: draw bounding boxes, build sample grids.

Used by all four modeling notebooks (Rolando, Diana, Jordan, Damir) to produce the
example-prediction figures required by the output contract.
"""

import cv2
import matplotlib.pyplot as plt
import numpy as np

# Distinct colors per label family so figures are easy to read at a glance.
_DEFAULT_COLOR = (255, 0, 0)  # BGR red
_LABEL_COLORS = {
    "stamp": (0, 140, 255),      # orange
    "signature": (255, 0, 255),  # magenta
}


def draw_boxes(image: np.ndarray, boxes: list[dict], thickness: int = 2) -> np.ndarray:
    """Draw labeled bounding boxes on a copy of `image`.

    boxes: list of dicts with 'label', 'xmin', 'ymin', 'xmax', 'ymax', optional 'confidence'.
    """
    out = image.copy()
    for box in boxes:
        color = _LABEL_COLORS.get(box["label"], _DEFAULT_COLOR)
        pt1 = (int(box["xmin"]), int(box["ymin"]))
        pt2 = (int(box["xmax"]), int(box["ymax"]))
        cv2.rectangle(out, pt1, pt2, color, thickness)

        label_text = box["label"]
        if "confidence" in box and box["confidence"] is not None:
            label_text += f" {box['confidence']:.2f}"
        cv2.putText(
            out, label_text, (pt1[0], max(0, pt1[1] - 6)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, thickness,
        )
    return out


def show_image_grid(images: list[np.ndarray], titles: list[str] | None = None, cols: int = 4, save_path=None) -> None:
    """Display (and optionally save) a grid of images — used for sample_invoice_grid.png,
    preprocessing_examples.png, and *_detection_examples.png outputs."""
    n = len(images)
    rows = (n + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(4 * cols, 4 * rows))
    axes = np.atleast_1d(axes).flatten()

    for i, ax in enumerate(axes):
        if i < n:
            img = images[i]
            # matplotlib expects RGB; cv2 images are BGR.
            if len(img.shape) == 3 and img.shape[2] == 3:
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            ax.imshow(img, cmap="gray" if len(img.shape) == 2 else None)
            if titles:
                ax.set_title(titles[i], fontsize=10)
        ax.axis("off")

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"Saved figure to {save_path}")
    plt.show()
