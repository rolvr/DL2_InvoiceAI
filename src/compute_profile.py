"""
compute_profile.py — shared compute-budget profiles for training/inference notebooks.

This project is developed and orchestrated on a CPU-only Windows machine, but each team
member also has the option of running their notebook on Google Colab with a GPU/TPU
available. Rather than hand-tune training knobs (epochs, image size, batch size, worker
count, how many images to subsample per class) separately in each environment -- which
tends to make the local and Colab notebooks silently drift apart -- every modeling notebook
should pull its knobs from `get_profile()` here, so there is exactly one definition of what
"local CPU budget" and "Colab GPU budget" mean project-wide.

Two named profiles:

- ``local_cpu``  — time-boxed for a CPU-only machine (no CUDA). Small image size, few
  epochs, small batch, `workers=0` (required for multiprocessing DataLoader workers on
  Windows), and a per-class image subsample cap so a full notebook run finishes in well
  under an hour.
- ``colab_gpu``  — generous budget for a Colab T4/L4/A100 runtime. Larger image size, many
  more epochs, bigger batch, a couple of DataLoader workers, and no image subsampling (use
  the full available dataset per class).

Not every notebook will use every key (e.g. an OCR notebook may not care about ``imgsz``),
but all keys are always present in the returned dict so callers can use `.get(...)` freely
or just read the ones they need.

Usage:
    from src.compute_profile import get_profile
    profile = get_profile()  # auto-detect, or set IIP_COMPUTE_PROFILE env var, or pass a name
    model.train(epochs=profile["epochs"], imgsz=profile["imgsz"], batch=profile["batch"],
                workers=profile["workers"], device=profile["device"])
"""

import os

_VALID_NAMES = {"auto", "local_cpu", "colab_gpu"}

_PROFILES = {
    "local_cpu": {
        "profile_name": "local_cpu",
        "epochs": 10,
        "imgsz": 416,
        "batch": 8,
        "workers": 0,
        "patience": 10,
        "device": "cpu",
        "max_images_per_class": 250,
    },
    "colab_gpu": {
        "profile_name": "colab_gpu",
        "epochs": 100,
        "imgsz": 960,
        "batch": 16,
        "workers": 2,
        "patience": 20,
        "device": 0,
        "max_images_per_class": None,  # no subsampling -- use the full available dataset
    },
}


def _cuda_available() -> bool:
    """Best-effort CUDA detection that never raises if torch isn't importable."""
    try:
        import torch  # local import: keep this module dependency-light / import-safe
        return bool(torch.cuda.is_available())
    except Exception:
        return False


def get_profile(name: str | None = None) -> dict:
    """Resolve and return a compute-budget profile dict.

    Resolution order (first non-``None``/non-``"auto"`` wins):
        1. explicit `name` argument
        2. `IIP_COMPUTE_PROFILE` environment variable
        3. auto-detect: CUDA available -> "colab_gpu", else -> "local_cpu"

    Accepted values (case-insensitive): "auto", "local_cpu", "colab_gpu". Any other value
    falls back to auto-detect (with a printed warning) rather than raising, so a typo'd env
    var can't silently break a notebook run.

    Returns a dict with at least: epochs, imgsz, batch, workers, patience, device,
    max_images_per_class, profile_name.
    """
    candidate = name or os.environ.get("IIP_COMPUTE_PROFILE") or "auto"
    candidate = candidate.strip().lower()

    if candidate not in _VALID_NAMES:
        print(f"[compute_profile] Unrecognized profile '{candidate}' -- falling back to auto-detect.")
        candidate = "auto"

    if candidate == "auto":
        candidate = "colab_gpu" if _cuda_available() else "local_cpu"

    return dict(_PROFILES[candidate])  # shallow copy -- callers should not mutate the shared dict
