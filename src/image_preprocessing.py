"""
image_preprocessing.py — basic image preprocessing shared across notebooks.

Owner: Rolando (data ingestion), used downstream by Diana/Jordan/Damir before detection/OCR.
Every function takes and returns a numpy array (BGR, as read by cv2.imread) unless noted.
"""

import cv2
import numpy as np


def to_grayscale(image: np.ndarray) -> np.ndarray:
    """Convert a BGR image to single-channel grayscale."""
    if len(image.shape) == 2:
        return image  # already grayscale
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def resize_image(image: np.ndarray, target_size: tuple[int, int] = (1024, 1024), keep_aspect: bool = True) -> np.ndarray:
    """Resize to target_size (width, height). If keep_aspect, pads with white instead of
    distorting the image — important for invoices where distortion would confuse layout
    detection."""
    if not keep_aspect:
        return cv2.resize(image, target_size)

    h, w = image.shape[:2]
    target_w, target_h = target_size
    scale = min(target_w / w, target_h / h)
    new_w, new_h = int(w * scale), int(h * scale)
    resized = cv2.resize(image, (new_w, new_h))

    channels = 1 if len(image.shape) == 2 else image.shape[2]
    canvas_shape = (target_h, target_w) if channels == 1 else (target_h, target_w, channels)
    canvas = np.full(canvas_shape, 255, dtype=image.dtype)
    canvas[0:new_h, 0:new_w] = resized
    return canvas


def denoise_image(image: np.ndarray) -> np.ndarray:
    """Light denoising — fastNlMeans works well on scanned document images."""
    if len(image.shape) == 2:
        return cv2.fastNlMeansDenoising(image, h=10)
    return cv2.fastNlMeansDenoisingColored(image, h=10, hColor=10)


def threshold_image(image: np.ndarray) -> np.ndarray:
    """Adaptive threshold to binarize a (grayscale) document image — improves OCR contrast."""
    gray = to_grayscale(image)
    return cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15
    )


def deskew_image(image: np.ndarray) -> np.ndarray:
    """Estimate and correct small rotation (skew) in a scanned document.

    Uses the minAreaRect of thresholded foreground pixels — good enough for the small skew
    angles typical of scanned/photographed invoices. Not a full perspective-correction
    solution; if input images are already fairly straight this is a no-op in practice.
    """
    gray = to_grayscale(image)
    inverted = cv2.bitwise_not(gray)
    thresh = cv2.threshold(inverted, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]

    coords = np.column_stack(np.where(thresh > 0))
    if coords.size == 0:
        return image  # nothing to deskew

    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle

    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(
        image, rotation_matrix, (w, h),
        flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE,
    )


def preprocess_pipeline(
    image: np.ndarray,
    do_grayscale: bool = True,
    do_denoise: bool = True,
    do_deskew: bool = True,
    do_threshold: bool = False,
    target_size: tuple[int, int] | None = (1024, 1024),
) -> np.ndarray:
    """Run the standard preprocessing chain. Threshold is off by default because binarized
    images are usually only wanted right before OCR, not for CNN/SSD detection input."""
    out = image
    if do_deskew:
        out = deskew_image(out)
    if do_denoise:
        out = denoise_image(out)
    if do_grayscale:
        out = to_grayscale(out)
    if do_threshold:
        out = threshold_image(out)
    if target_size:
        out = resize_image(out, target_size)
    return out
